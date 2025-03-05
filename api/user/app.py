from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_restx import Api, Resource, fields
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
import json
import uuid
import os
import base64


##### Configuration #####
# Define API version and root path
API_VERSION = 'v1'
API_ROOT = f'/{API_VERSION}/api'

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
api = Api(app, version=API_VERSION, title='User API', description='User API for Yorkshire Crypto Exchange')


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
    auth_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('user_account.user_id', ondelete='CASCADE'), nullable=False)
    password_hashed = db.Column(db.LargeBinary, nullable=False)
    salt = db.Column(db.LargeBinary, nullable=False)
    hashing_algorithm = db.Column(db.String(50), nullable=False)
    created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = db.relationship('UserAccount', back_populates='authentication')

class UserAddress(db.Model):
    __tablename__ = 'user_address'
    address_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), db.ForeignKey('user_account.user_id', ondelete='CASCADE'), nullable=False)
    street_number = db.Column(db.String(10), nullable=False)
    street_name = db.Column(db.String(100), nullable=False)
    unit_number = db.Column(db.String(20))
    building_name = db.Column(db.String(100))
    district = db.Column(db.String(100))
    city = db.Column(db.String(100), nullable=False)
    state_province = db.Column(db.String(100), nullable=False)
    postal_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(100), nullable=False)
    created = db.Column(db.DateTime(timezone=True), server_default=func.now())
    updated = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = db.relationship('UserAccount', back_populates='addresses')


##### API Models - flask restx API autodoc #####
# To use flask restx, you will have to define API models with their input types
# Define API Models
user_model = api.model('UserAccount', {
    'user_id': fields.String(readOnly=True, description='The unique identifier of a user'),
    'username': fields.String(required=True, description='The username'),
    'fullname': fields.String(required=True, description='The full name'),
    'phone': fields.String(required=True, description='The phone number'),
    'email': fields.String(required=True, description='The email address')
})

auth_model = api.model('UserAuthenticate', {
    'auth_id': fields.String(readOnly=True, description='The authentication ID'),
    'user_id': fields.String(required=True, description='The associated user ID'),
    'hashing_algorithm': fields.String(required=True, description='The hashing algorithm used')
})

address_model = api.model('UserAddress', {
    'address_id': fields.String(readOnly=True, description='The unique identifier of an address'),
    'user_id': fields.String(required=True, description='The associated user ID'),
    'street_number': fields.String(required=True, description='The street number'),
    'street_name': fields.String(required=True, description='The street name'),
    'city': fields.String(required=True, description='The city'),
    'state_province': fields.String(required=True, description='The state or province'),
    'postal_code': fields.String(required=True, description='The postal code'),
    'country': fields.String(required=True, description='The country')
})


##### API actions - flask restx API autodoc #####
# To use flask restx, you will also have to seperate the CRUD actions from the DB table classes

# CRUD for UserAccount
@api.route(f'{API_ROOT}/user/account')
class UserAccountListResource(Resource):
    @api.marshal_list_with(user_model)
    def get(self):
        """Fetch all user accounts"""
        return UserAccount.query.all()

    @api.expect(user_model)
    @api.marshal_with(user_model, code=201)
    def post(self):
        """Create a new user account"""
        data = request.json
        new_user = UserAccount(
            username=data.get('username'),
            fullname=data.get('fullname'),
            phone=data.get('phone'),
            email=data.get('email'),
            # In a real scenario, handle address_id properly or default
            address_id=uuid.uuid4() # placeholder
        )
        db.session.add(new_user)
        db.session.commit()
        return new_user, 201

@api.route(f'{API_ROOT}/user/account/<uuid:user_id>')
@api.param('user_id', 'The unique identifier of a user')
class UserAccountResource(Resource):
    @api.marshal_with(user_model)
    def get(self, user_id):
        """Fetch a user account by ID"""
        user = UserAccount.query.get(user_id)
        if not user:
            api.abort(404, 'User not found')
        return user

    @api.expect(user_model)
    @api.marshal_with(user_model)
    def put(self, user_id):
        """Update an existing user account"""
        user = UserAccount.query.get(user_id)
        if not user:
            api.abort(404, 'User not found')
        data = request.json
        user.username = data.get('username', user.username)
        user.fullname = data.get('fullname', user.fullname)
        user.phone = data.get('phone', user.phone)
        user.email = data.get('email', user.email)
        db.session.commit()
        return user

    def delete(self, user_id):
        """Delete an existing user account"""
        user = UserAccount.query.get(user_id)
        if not user:
            api.abort(404, 'User not found')
        db.session.delete(user)
        db.session.commit()
        return {'message': 'User deleted successfully'}

# CRUD for UserAuthenticate
@api.route(f'{API_ROOT}/user/authenticate')
class UserAuthenticateListResource(Resource):
    @api.marshal_list_with(auth_model)
    def get(self):
        """Fetch all authentication records"""
        return UserAuthenticate.query.all()

    @api.expect(auth_model)
    @api.marshal_with(auth_model, code=201)
    def post(self):
        """Create a new authentication record"""
        data = request.json
        new_auth = UserAuthenticate(
            user_id=data.get('user_id'),
            hashing_algorithm=data.get('hashing_algorithm'),
            password_hashed=b'temp',  # placeholder
            salt=b'temp'             # placeholder
        )
        db.session.add(new_auth)
        db.session.commit()
        return new_auth, 201

@api.route(f'{API_ROOT}/user/authenticate/<uuid:auth_id>')
@api.param('auth_id', 'The unique identifier of an authentication record')
class UserAuthenticateResource(Resource):
    @api.marshal_with(auth_model)
    def get(self, auth_id):
        """Fetch an authentication record by ID"""
        auth = UserAuthenticate.query.get(auth_id)
        if not auth:
            api.abort(404, 'Authentication record not found')
        return auth

    @api.expect(auth_model)
    @api.marshal_with(auth_model)
    def put(self, auth_id):
        """Update an existing authentication record"""
        auth = UserAuthenticate.query.get(auth_id)
        if not auth:
            api.abort(404, 'Authentication record not found')
        data = request.json
        auth.user_id = data.get('user_id', str(auth.user_id))
        auth.hashing_algorithm = data.get('hashing_algorithm', auth.hashing_algorithm)
        # In a real scenario, handle password hashing & salt properly
        db.session.commit()
        return auth

    def delete(self, auth_id):
        """Delete an existing authentication record"""
        auth = UserAuthenticate.query.get(auth_id)
        if not auth:
            api.abort(404, 'Authentication record not found')
        db.session.delete(auth)
        db.session.commit()
        return {'message': 'Authentication record deleted successfully'}

# CRUD for UserAddress
@api.route(f'{API_ROOT}/user/address')
class UserAddressListResource(Resource):
    @api.marshal_list_with(address_model)
    def get(self):
        """Fetch all user addresses"""
        return UserAddress.query.all()

    @api.expect(address_model)
    @api.marshal_with(address_model, code=201)
    def post(self):
        """Create a new user address"""
        data = request.json
        new_address = UserAddress(
            user_id=data.get('user_id'),
            street_number=data.get('street_number'),
            street_name=data.get('street_name'),
            city=data.get('city'),
            state_province=data.get('state_province'),
            postal_code=data.get('postal_code'),
            country=data.get('country')
        )
        db.session.add(new_address)
        db.session.commit()
        return new_address, 201

@api.route(f'{API_ROOT}/user/address/<uuid:address_id>')
@api.param('address_id', 'The unique identifier of a user address')
class UserAddressResource(Resource):
    @api.marshal_with(address_model)
    def get(self, address_id):
        """Fetch a user address by ID"""
        address = UserAddress.query.get(address_id)
        if not address:
            api.abort(404, 'Address not found')
        return address

    @api.expect(address_model)
    @api.marshal_with(address_model)
    def put(self, address_id):
        """Update an existing user address"""
        address = UserAddress.query.get(address_id)
        if not address:
            api.abort(404, 'Address not found')
        data = request.json
        address.street_number = data.get('street_number', address.street_number)
        address.street_name = data.get('street_name', address.street_name)
        address.city = data.get('city', address.city)
        address.state_province = data.get('state_province', address.state_province)
        address.postal_code = data.get('postal_code', address.postal_code)
        address.country = data.get('country', address.country)
        db.session.commit()
        return address

    def delete(self, address_id):
        """Delete an existing user address"""
        address = UserAddress.query.get(address_id)
        if not address:
            api.abort(404, 'Address not found')
        db.session.delete(address)
        db.session.commit()
        return {'message': 'Address deleted successfully'}


##### Seeding #####
# Provide seed data for all tables
def seed_data():
    try:
        with open("seeddata.json", "r") as file:
            data = json.load(file)

        # -- 1) Insert UserAccount data (Check for existing users to prevent duplicates) --
        accounts_data = data.get("accounts", [])
        existing_usernames = {u.username for u in UserAccount.query.all()}  # Fetch existing usernames

        for acc in accounts_data:
            if acc["username"] in existing_usernames:
                print(f"Skipping user '{acc['username']}' as it already exists.")
                continue  # Skip existing users
            
            new_user = UserAccount(
                username=acc["username"],
                fullname=acc["fullname"],
                phone=acc["phone"],
                email=acc["email"]
            )
            db.session.add(new_user)
        db.session.commit()  # Commit so new users get their user_id

        # Create a lookup for user_id by username (for linking authentications and addresses)
        user_lookup = {u.username: u.user_id for u in UserAccount.query.all()}

        # -- 2) Insert UserAuthenticate data (Check if user exists) --
        auth_data = data.get("authentications", [])
        for auth in auth_data:
            username = auth["username"]
            user_id = user_lookup.get(username)
            if not user_id:
                print(f"Skipping authentication for unknown user '{username}'")
                continue  # Skip if the user does not exist

            existing_auth = UserAuthenticate.query.filter_by(user_id=user_id).first()
            if existing_auth:
                print(f"Skipping authentication for user '{username}' as it already exists.")
                continue  # Prevent duplicate authentication records

            new_auth = UserAuthenticate(
                user_id=user_id,
                password_hashed=base64.b64decode(auth.get("password_hashed", "c29tZWhhc2hlZHBhc3N3b3Jk")),  # Decode base64 to binary
                salt=base64.b64decode(auth.get("salt", "c29tZXNhbHQ=")),  # Decode base64 to binary
                hashing_algorithm=auth["hashing_algorithm"]
            )
            db.session.add(new_auth)
        db.session.commit()

        # -- 3) Insert UserAddress data (Ensure user exists) --
        addresses_data = data.get("addresses", [])
        for addr in addresses_data:
            username = addr["username"]
            user_id = user_lookup.get(username)
            if not user_id:
                print(f"Skipping address for unknown user '{username}'")
                continue  # Skip if user does not exist

            existing_address = UserAddress.query.filter_by(user_id=user_id).first()
            if existing_address:
                print(f"Skipping address for user '{username}' as it already exists.")
                continue  # Prevent duplicate addresses

            new_address = UserAddress(
                user_id=user_id,
                street_number=addr["street_number"],
                street_name=addr["street_name"],
                unit_number=addr.get("unit_number"),
                building_name=addr.get("building_name"),
                district=addr.get("district"),
                city=addr["city"],
                state_province=addr["state_province"],
                postal_code=addr["postal_code"],
                country=addr["country"]
            )
            db.session.add(new_address)
        db.session.commit()

        print("Seed data successfully loaded from seeddata.json")

    except IntegrityError as e:
        db.session.rollback()
        print(f"Data seeding failed due to integrity error: {e}")
    except FileNotFoundError:
        print("seeddata.json not found. Skipping seeding.")

if __name__ == '__main__':
    with app.app_context():
        seed_data()
    app.run(host='0.0.0.0', port=5000, debug=True)