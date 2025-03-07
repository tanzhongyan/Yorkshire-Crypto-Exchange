from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
import json
import uuid
import os


##### Configuration #####
# Define API version and root path
API_VERSION = 'v1'
API_ROOT = f'/{API_VERSION}/api/user'

app = Flask(__name__)
CORS(app)

# Detect if running inside Docker
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"

# Set Database Configuration Dynamically
if RUNNING_IN_DOCKER:
    DB_HOST = "postgres"  # Docker network name
    DB_PORT = "5432"
else:
    DB_HOST = "localhost"  # Local environment
    DB_PORT = "5433"

DB_NAME = os.getenv("DB_NAME", "user_db")
DB_USER = os.getenv("DB_USER", "user")
DB_PASS = os.getenv("DB_PASS", "password")

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask swagger (flask_restx) api documentation
# Creates API documentation automatically
blueprint = Blueprint('api',__name__,url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='User API', description='User API for Yorkshire Crypto Exchange')

# Register Blueprint with Flask app
app.register_blueprint(blueprint)

# Define namespaces to group api calls together
# Namespaces are essentially folders that group all APIs calls related to a table
# You can treat it as table_ns
# Its essential that you use this at your routes
account_ns = Namespace('account', description='Account related operations')
authenticate_ns = Namespace('authenticate', description='Authenticate related operations')
address_ns = Namespace('address', description='Address related operations')

##### DB table classes declaration - flask migrate #####
# To use flask migrate, you have to create classes for the table of the entity
# Use these classes to define their data type, uniqueness, nullability, and relationships
# This will auto generate migration code for the database, removing the need for us to manually code SQL to initialise database
# Separate the CRUD functions outside of the classes. Better for separation of concern.
class UserAccount(db.Model):
    __tablename__ = 'user_account'
    user_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = db.Column(db.String(50), unique=True, nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)

    # Relationships
    authentication = db.relationship('UserAuthenticate', back_populates='user', uselist=False, cascade='all, delete-orphan')
    addresses = db.relationship('UserAddress', back_populates='user', cascade='all, delete-orphan')

class UserAuthenticate(db.Model):
    __tablename__ = 'user_authenticate'
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('user_account.user_id', ondelete='CASCADE'), nullable=False, primary_key=True)
    password_hashed = db.Column(db.String, nullable=False)
    updated = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = db.relationship('UserAccount', back_populates='authentication', uselist=False)

class UserAddress(db.Model):
    __tablename__ = 'user_address'
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('user_account.user_id', ondelete='CASCADE'), nullable=False, primary_key=True)
    street_number = db.Column(db.String(10), nullable=False)
    street_name = db.Column(db.String(100), nullable=False)
    unit_number = db.Column(db.String(20))
    building_name = db.Column(db.String(100))
    district = db.Column(db.String(100))
    city = db.Column(db.String(100), nullable=False)
    state_province = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    updated = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = db.relationship('UserAccount', back_populates='addresses', uselist=False)


##### API Models - flask restx API autodoc #####
# To use flask restx, you will have to define API models with their input types
# For all API models, add a comment to the top to signify its importance
# E.g. Input/Output One/Many user account

# Output One/Many user account
user_output_model = account_ns.model('UserOutput', {
    'userId': fields.String(attribute='user_id', readOnly=True, description='The unique identifier of a user'),
    'username': fields.String(required=True, description='The username'),
    'fullname': fields.String(required=True, description='The full name'),
    'phone': fields.String(required=True, description='The phone number'),
    'email': fields.String(required=True, description='The email address')
})

# Input One user account
user_input_model = account_ns.model('UserInput', {
    'username': fields.String(required=True, description='The username'),
    'fullname': fields.String(required=True, description='The full name'),
    'phone': fields.String(required=True, description='The phone number'),
    'email': fields.String(required=True, description='The email address')
})

# output one user authenticate
auth_output_model = authenticate_ns.model('AuthOutput', {
    'userId': fields.String(attribute='user_id', required=True, description='The associated user ID'),
    'passwordHashed': fields.String(attribute='password_hashed', required=True, description='The hashed password')
})

# Input one user authenticate
auth_input_model = authenticate_ns.model('AuthInput', {
    'passwordHashed': fields.String(attribute='password_hashed', required=True, description='The hashed password')
})

# output one user address
address_output_model = address_ns.model('AddressOutput', {
    'userId': fields.String(attribute='user_id', required=True, description='The associated user ID'),
    'streetNumber': fields.String(attribute='street_number',required=True, description='The street number'),
    'streetName': fields.String(attribute='street_name',required=True, description='The street name'),
    'unitNumber': fields.String(attribute='unit_number',required=False, description='The unit number'),
    'buildingName': fields.String(attribute='building_name',required=False, description='The building name'),
    'district': fields.String(attribute='district',required=False, description='The district'),
    'city': fields.String(required=True, description='The city'),
    'stateProvince': fields.String(attribute='state_province',required=True, description='The state or province'),
    'postalCode': fields.String(attribute='postal_code',required=True, description='The postal code'),
    'country': fields.String(required=True, description='The country')
})

# input one user address
address_input_model = address_ns.model('AddressInput', {
    'streetNumber': fields.String(attribute='street_number',required=True, description='The street number'),
    'streetName': fields.String(attribute='street_name',required=True, description='The street name'),
    'unitNumber': fields.String(attribute='unit_number',required=False, description='The unit number'),
    'buildingName': fields.String(attribute='building_name',required=False, description='The building name'),
    'district': fields.String(attribute='district',required=False, description='The district'),
    'city': fields.String(required=True, description='The city'),
    'stateProvince': fields.String(attribute='state_province',required=True, description='The state or province'),
    'postalCode': fields.String(attribute='postal_code',required=True, description='The postal code'),
    'country': fields.String(required=True, description='The country')
})


##### API actions - flask restx API autodoc #####
# To use flask restx, you will also have to seperate the CRUD actions from the DB table classes

# CRUD for UserAccount
@account_ns.route('')
class UserAccountListResource(Resource):
    @account_ns.marshal_list_with(user_output_model)
    def get(self):
        """Fetch all user accounts"""
        return UserAccount.query.all()

    @account_ns.expect(user_input_model, validate=True)
    @account_ns.marshal_with(user_output_model, code=201)
    def post(self): 
        """Create a new user account"""
        data = request.json
        new_user = UserAccount(
            username=data.get('username'),
            fullname=data.get('fullname'),
            phone=data.get('phone'),
            email=data.get('email')
        )
        try:
            db.session.add(new_user)
            db.session.commit()
            return new_user, 201
        except:
            account_ns.abort(400, 'Username or email already exists')

@account_ns.route('/<uuid:userId>')
@account_ns.param('userId', 'The unique identifier of a user') # Alternative code: @account_ns.doc(params={'userId':'The unique identifier of a user'}) 
class UserAccountResource(Resource):
    @account_ns.marshal_with(user_output_model)
    def get(self, userId):
        """Fetch a user account by ID"""
        user = UserAccount.query.get_or_404(userId, description='User not found')
        return user

    @account_ns.expect(user_input_model, validate=True)
    @account_ns.marshal_with(user_output_model)
    def put(self, userId):
        """Update an existing user account"""
        user = UserAccount.query.get_or_404(userId, description='User not found')
        data = request.json
        user.username = data.get('username', user.username)
        user.fullname = data.get('fullname', user.fullname)
        user.phone = data.get('phone', user.phone)
        user.email = data.get('email', user.email)
        try:
            db.session.commit()
            return user
        except:
            account_ns.abort(400, 'Username or email already exists')

    def delete(self, userId):
        """Delete an existing user account"""
        user = UserAccount.query.get_or_404(userId, description='User not found')
        db.session.delete(user)
        db.session.commit()
        return {'message': 'User deleted successfully'}

# CRU for UserAuthenticate. No delete as delete is cascaded from account table.
@authenticate_ns.route('/<uuid:userId>')
@authenticate_ns.param('userId', 'The unique identifier of a user')
class UserAuthenticateResource(Resource):
    @authenticate_ns.marshal_with(auth_output_model)
    def get(self, userId):
        """Fetch authentication details by user ID"""
        auth = UserAuthenticate.query.get(userId)
        if not auth:
            authenticate_ns.abort(404, 'Authentication record not found')
        return auth

    @authenticate_ns.expect(auth_input_model, validate=True)
    @authenticate_ns.marshal_with(auth_output_model, code=201)
    def post(self, userId):
        """Create a new authentication record (password pre-hashed)"""
        data = request.json
        existing_auth = UserAuthenticate.query.get(userId)
        if existing_auth:
            authenticate_ns.abort(400, 'Authentication record already exists')

        new_auth = UserAuthenticate(
            user_id=userId,
            password_hashed=data.get('passwordHashed')
        )
        db.session.add(new_auth)
        db.session.commit()
        return new_auth, 201

    @authenticate_ns.expect(auth_input_model, validate=True)
    @authenticate_ns.marshal_with(auth_output_model)
    def put(self, userId):
        """Update password for a user"""
        auth = UserAuthenticate.query.get_or_404(userId, description="Authentication record not found")
        data = request.json
        auth.password_hashed = data.get("passwordHashed", auth.password_hashed)
        try:
            db.session.commit()
            return auth
        except:
            account_ns.abort(500, 'Something went wrong')
        
# CRU for UserAddress. No delete as delete is cascaded from account table.
@address_ns.route('/<uuid:userId>')
@address_ns.param('userId', 'The unique identifier of a user') 
class UserAddressResource(Resource):
    @address_ns.marshal_with(address_output_model)
    def get(self, userId):
        """Fetch a user address by User ID (One-to-One Relationship)"""
        address = UserAddress.query.filter_by(user_id=userId).first()
        if not address:
            address_ns.abort(404, 'Address not found')
        return address

    @address_ns.expect(address_input_model, validate=True)
    @address_ns.marshal_with(address_output_model, code=201)
    def post(self, userId):
        """Create a new user address (User ID is taken from the path, not body)"""
        existing_address = UserAddress.query.filter_by(user_id=userId).first()
        if existing_address:
            address_ns.abort(400, 'Address already exists for this user')

        data = request.json
        new_address = UserAddress(
            user_id=userId,  # ✅ user_id from the path, not from request body
            street_number=data.get('streetNumber'),
            street_name=data.get('streetName'),
            unit_number=data.get('unitNumber'),
            building_name=data.get('buildingName'),
            district=data.get('district'),
            city=data.get('city'),
            state_province=data.get('stateProvince'),
            postal_code=data.get('postalCode'),
            country=data.get('country')
        )
        db.session.add(new_address)
        db.session.commit()
        return new_address, 201

    @address_ns.expect(address_input_model, validate=True)
    @address_ns.marshal_with(address_output_model)
    def put(self, userId):
        """Update an existing user address (using user_id in path)"""
        address = UserAddress.query.filter_by(user_id=userId).first()
        if not address:
            address_ns.abort(404, 'Address not found')

        data = request.json
        address.street_number = data.get('streetNumber', address.street_number)
        address.street_name = data.get('streetName', address.street_name)
        address.unit_number=data.get('unitNumber', address.unit_number),
        address.building_name=data.get('buildingName', address.building_name),
        address.district=data.get('district', address.district),
        address.city = data.get('city', address.city)
        address.state_province = data.get('stateProvince', address.state_province)
        address.postal_code = data.get('postalCode', address.postal_code)
        address.country = data.get('country', address.country)

        db.session.commit()
        return address

##### Seeding #####
# Provide seed data for all tables
def seed_data():
    try:
        with open("seeddata.json", "r") as file:
            data = json.load(file)

        # 1) Insert UserAccount data
        user_accounts_data = data.get("userAccounts", [])
        existing_usernames = {u.username for u in UserAccount.query.all()}

        for acc in user_accounts_data:
            # Skip if user already exists
            if acc["userName"] in existing_usernames:
                print(f"Skipping user '{acc['userName']}' as it already exists.")
                continue

            new_user = UserAccount(
                username=acc["userName"],
                fullname=acc["fullName"],
                phone=acc["phoneNumber"],
                email=acc["email"]
            )
            db.session.add(new_user)
        db.session.commit()

        # Create a lookup for user_id by username
        user_lookup = {u.username: u.user_id for u in UserAccount.query.all()}

        # 2) Insert UserAuthenticate data
        user_authentications_data = data.get("userAuthentications", [])
        for auth in user_authentications_data:
            username = auth["userName"]
            user_id = user_lookup.get(username)

            # Skip if the user does not exist
            if not user_id:
                print(f"Skipping authentication for unknown user '{username}'")
                continue

            existing_auth = UserAuthenticate.query.filter_by(user_id=user_id).first()
            if existing_auth:
                print(f"Skipping authentication for user '{username}' as it already exists.")
                continue

            new_auth = UserAuthenticate(
                user_id=user_id,
                password_hashed=auth.get("passwordHashed", "c29tZWhhc2hlZHBhc3N3b3Jk")
            )
            db.session.add(new_auth)
        db.session.commit()

        # 3) Insert UserAddress data
        user_addresses_data = data.get("userAddresses", [])
        for addr in user_addresses_data:
            username = addr["userName"]
            user_id = user_lookup.get(username)

            # Skip if user does not exist
            if not user_id:
                print(f"Skipping address for unknown user '{username}'")
                continue

            existing_address = UserAddress.query.filter_by(user_id=user_id).first()
            if existing_address:
                print(f"Skipping address for user '{username}' as it already exists.")
                continue

            new_address = UserAddress(
                user_id=user_id,
                street_number=addr["streetNumber"],
                street_name=addr["streetName"],
                unit_number=addr.get("unitNumber"),
                building_name=addr.get("buildingName"),
                district=addr.get("district"),
                city=addr["city"],
                state_province=addr["stateProvince"],
                postal_code=addr["postalCode"],
                country=addr["country"]
            )
            db.session.add(new_address)
        db.session.commit()

        print("Seed data successfully loaded from seeddata.json.")

    except IntegrityError as e:
        db.session.rollback()
        print(f"Data seeding failed due to integrity error: {e}")
    except FileNotFoundError:
        print("seeddata.json not found. Skipping seeding.")

# Add name spaces into api
api.add_namespace(account_ns)
api.add_namespace(authenticate_ns)
api.add_namespace(address_ns)

if __name__ == '__main__':
    with app.app_context():
        seed_data()
    app.run(host='0.0.0.0', port=5000, debug=True)