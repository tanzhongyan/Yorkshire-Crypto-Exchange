from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.exc import IntegrityError
from twilio.rest import Client
from dotenv import load_dotenv
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import bcrypt
import json
import jwt
import uuid
import os
import time
import smtplib

##### Configuration #####
# Define API version and root path
API_VERSION = 'v1'
API_ROOT = f'/api/{API_VERSION}/user'

app = Flask(__name__)
CORS(app)

# Load environment variables
load_dotenv()

# Declare website location
WEBAPP_URL = "http://localhost:3000"

# In-memory storage for reset tokens (in production, use a database table)
reset_tokens = {}

# Detect if running inside Docker
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"
JWT_KEY = os.getenv("JWT_KEY", "iloveesd")
JWT_SECRET = os.getenv("JWT_SECRET", "esdisfun")

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
    'userId': fields.String(attribute='user_id', readOnly=True, description='The unique identifier of a user',
                example='a7c396e2-8370-4975-820e-c5ee8e3875c0'),
    'username': fields.String(required=True, description='The username',
                example='test'),
    'fullname': fields.String(required=True, description='The full name',
                example='Test User'),
    'phone': fields.String(required=True, description='The phone number',
                example='12345678'),
    'email': fields.String(required=True, description='The email address',
                example='test@test.com')
})

# Input One user account
user_input_model = account_ns.model('UserInput', {
    'username': fields.String(required=True, description='The username',
                example='test'),
    'fullname': fields.String(required=True, description='The full name',
                example='Test User'),
    'phone': fields.String(required=True, description='The phone number',
                example='12345678'),
    'email': fields.String(required=True, description='The email address',
                example='test@test.com')
})

# output one user authenticate
auth_output_model = authenticate_ns.model('AuthOutput', {
    'userId': fields.String(attribute='user_id', required=True, description='The associated user ID',
                example='a7c396e2-8370-4975-820e-c5ee8e3875c0'),
    'passwordHashed': fields.String(attribute='password_hashed', required=True, description='The hashed password',
                example='$2b$12$qHXz/XGhT57M.vltsTzoNOKVBDL2BHN0q0EEgXsNQ3lKD6rn3Y1eG')
})

# Input one user authenticate
auth_input_model = authenticate_ns.model('AuthInput', {
    'password': fields.String(attribute='password', required=True, description='The password',
                example='test12345')
})

# Input model for authentication
auth_model = authenticate_ns.model(
    "AuthenticateUser",
    {
        "identifier": fields.String(required=True, description="Username or Email",
                    example='test'),
        "password": fields.String(required=True, description="User password",
                    example='test12345'),
    },
)

# Success response model
auth_success_response = authenticate_ns.model(
    "AuthSuccessResponse",
    {
        "message": fields.String(description="Authentication successful",
                    example='Authentication successful'),
        "userId": fields.String(attribute='user_id', description="Authenticated User ID",
                    example='a7c396e2-8370-4975-820e-c5ee8e3875c0'),
        "token": fields.String(description="JWT authentication token",
                    example='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjoiYTdjMzk2ZTItODM3MC00OTc1LTgyMGUtYzVlZThlMzg3NWMwIiwiZXhwIjoxNjYwMDAwMDAwfQ.signature')
    },
)

# Error response model
auth_error_response = authenticate_ns.model(
    "AuthErrorResponse",
    {
        "error": fields.String(description="Error message",
                example='Authentication failed'),
        "details": fields.String(description="Additional error details",
                example='Invalid username or password'),
    },
)

# Reset password request model
reset_password_request_model = authenticate_ns.model(
    "ResetPasswordRequest",
    {
        "email": fields.String(required=True, description="The email address of the user",
                example='test@test.com'),
    },
)

# Reset password model (actual reset with token)
reset_password_model = authenticate_ns.model(
    "ResetPassword",
    {
        "token": fields.String(required=True, description="The reset token",
                example='eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbWFpbCI6InRlc3RAdGVzdC5jb20iLCJleHAiOjE2NjAwMDAwMDB9.signature'),
        "newPassword": fields.String(required=True, description="The new password",
                example='newPassword123'),
    },
)

# Reset password response
reset_password_response = authenticate_ns.model(
    "ResetPasswordResponse",
    {
        "message": fields.String(description="Operation result message",
                example='Password has been reset successfully'),
    },
)

# output one user address
address_output_model = address_ns.model('AddressOutput', {
    'userId': fields.String(attribute='user_id', required=True, description='The associated user ID',
                example='a7c396e2-8370-4975-820e-c5ee8e3875c0'),
    'streetNumber': fields.String(attribute='street_number',required=True, description='The street number',
                example='Test'),
    'streetName': fields.String(attribute='street_name',required=True, description='The street name',
                example='Test Street'),
    'unitNumber': fields.String(attribute='unit_number',required=False, description='The unit number',
                example='Test'),
    'buildingName': fields.String(attribute='building_name',required=False, description='The building name',
                example='Test Building'),
    'district': fields.String(attribute='district',required=False, description='The district',
                example='Test District'),
    'city': fields.String(required=True, description='The city',
                example='Test City'),
    'stateProvince': fields.String(attribute='state_province',required=True, description='The state or province',
                example='Test State'),
    'postalCode': fields.String(attribute='postal_code',required=True, description='The postal code',
                example='Test123'),
    'country': fields.String(required=True, description='The country',
                example='Test Country')
})

# input one user address
address_input_model = address_ns.model('AddressInput', {
    'streetNumber': fields.String(attribute='street_number',required=True, description='The street number',
                example='Test'),
    'streetName': fields.String(attribute='street_name',required=True, description='The street name',
                example='Test Street'),
    'unitNumber': fields.String(attribute='unit_number',required=False, description='The unit number',
                example='Test'),
    'buildingName': fields.String(attribute='building_name',required=False, description='The building name',
                example='Test Building'),
    'district': fields.String(attribute='district',required=False, description='The district',
                example='Test District'),
    'city': fields.String(required=True, description='The city',
                example='Test City'),
    'stateProvince': fields.String(attribute='state_province',required=True, description='The state or province',
                example='Test State'),
    'postalCode': fields.String(attribute='postal_code',required=True, description='The postal code',
                example='Test123'),
    'country': fields.String(required=True, description='The country',
                example='Test Country')
})


##### Functions #####
# Add functions to this section to support API actions

# Password Functions
# Copied from https://www.geeksforgeeks.org/hashing-passwords-in-python-with-bcrypt/
def hash_password(password):
    """Hashes and salts the password"""
    # Convert password to bytes
    password_bytes = password.encode('utf-8')

    # Generate salt
    salt = bcrypt.gensalt()

    # Hash password
    hashed_password_bytes = bcrypt.hashpw(password_bytes,salt)
    return hashed_password_bytes.decode() #Decode to store as a string

def check_password(input_password,hashed_password):
    """Checks input password against stored password"""
    # Convert input passwords to bytes
    input_password_bytes = input_password.encode('utf-8')

    # Convert hashed password to bytes
    hashed_password_bytes = hashed_password.encode('utf-8')
    
    # Check password
    result = bcrypt.checkpw(input_password_bytes,hashed_password_bytes)
    return result

def generate_jwt_token(user_id):
    """Generate a JWT token with 1-hour expiration"""
    payload = {
        'sub': str(user_id),
        'exp': int(time.time()) + 3600,  # 1 hour expiry
        'iat': int(time.time()),
        'kid': JWT_KEY,  # Must match your Kong configuration
        'iss': JWT_KEY   # Add the issuer claim with the same value as kid
    }

    # Create the token using the same secret defined in Kong
    token = jwt.encode(payload, JWT_SECRET, algorithm='HS256')
    return token

def send_reset_email(to_email, reset_link):
    sender_email = os.getenv("GMAIL_USER")
    sender_password = os.getenv("GMAIL_PASSWORD")
    
    subject = "Password Reset Link - Yorkshire Crypto Exchange"
    body = f"""
    Hello,

    You requested a password reset. Click the link below to reset your password:
    {reset_link}

    If you didn’t request this, please ignore this email.

    Regards,
    Yorkshire Crypto Exchange Team
    """

    msg = MIMEMultipart()
    msg["From"] = sender_email
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        print(f"Password reset email sent to {to_email}")
    except Exception as e:
        print(f"Failed to send email: {e}")

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
            username=data.get('username').lower(),
            fullname=data.get('fullname').title(),
            phone=data.get('phone'),
            email=data.get('email').lower()
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
        user.username = data.get('username', user.username).lower()
        user.fullname = data.get('fullname', user.fullname).title()
        user.phone = data.get('phone', user.phone)
        user.email = data.get('email', user.email).lower()
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

# Search function for user id
@account_ns.route('/search')
class UserSearchResource(Resource):
    @account_ns.doc(params={"identifier": "The username or email of the user"})
    def get(self):
        """Fetch user details by username or email"""
        identifier = request.args.get("identifier").lower()
        if not identifier:
            account_ns.abort(400, "Username or email is required")

        # Query the User table for either username or email
        user = UserAccount.query.filter(
            (UserAccount.username == identifier) | (UserAccount.email == identifier)
        ).first()

        if not user:
            account_ns.abort(404, "User not found")

        return {"userId": str(user.user_id)}, 200 


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
            password_hashed=hash_password(data.get('password'))
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
        auth.password_hashed = hash_password(data.get("password", auth.password_hashed))
        try:
            db.session.commit()
            return auth
        except:
            account_ns.abort(500, 'Something went wrong')

@authenticate_ns.route("/login")
class AuthenticateUser(Resource):
    @authenticate_ns.expect(auth_model)
    @authenticate_ns.response(200, "Authentication successful", auth_success_response)
    @authenticate_ns.response(400, "Invalid credentials", auth_error_response)
    @authenticate_ns.response(500, "Internal Server Error", auth_error_response)
    def post(self):
        """Authenticate user using username/email and password"""
        data = request.json
        identifier = data.get("identifier").lower()
        input_password = data.get("password")

        if not identifier or not input_password:
            return {"error": "Missing required fields", "details": "Username/email and password are required"}, 400

        try:
            # Step 1: Fetch user details from UserAccount table
            user = UserAccount.query.filter(
                (UserAccount.username == identifier) | (UserAccount.email == identifier)
            ).first()

            if not user:
                return {"error": "User not found", "details": "Invalid username or email"}, 400

            user_id = str(user.user_id)

            # Step 2: Fetch authentication record from UserAuthenticate table
            auth = UserAuthenticate.query.filter_by(user_id=user_id).first()

            if not auth:
                return {"error": "Authentication record not found", "details": "No authentication data for this user"}, 400

            stored_hashed_password = auth.password_hashed

            if not stored_hashed_password:
                return {"error": "Invalid authentication response", "details": "Missing stored password"}, 500

            # Step 3: Verify password
            if not check_password(input_password, stored_hashed_password):
                return {"error": "Invalid credentials", "details": "Incorrect username/email or password"}, 400
            
            # step 4 Generate JWT token
            token = generate_jwt_token(user_id)

            return {
                "message": "Authentication successful", 
                "userId": user_id,
                "token": token
            }, 200
        
        except Exception as e:
            return {"error": "Internal Server Error", "details": str(e)}, 500

@authenticate_ns.route('/reset-password-request')
class ResetPasswordRequest(Resource):
    @authenticate_ns.expect(reset_password_request_model)
    @authenticate_ns.response(200, "Reset email sent", reset_password_response)
    def post(self):
        """Request a password reset link"""
        data = request.json
        email = data.get("email").lower()
        
        # Always return success to prevent email enumeration
        # (don't reveal if account exists)
        user = UserAccount.query.filter_by(email=email).first()
        if not user:
            # Still return success but don't send email
            # This prevents attackers from discovering valid emails
            return {"message": "If the email exists, a reset link has been sent"}, 200
            
        # Generate secure token (NOT a JWT)
        reset_token = str(uuid.uuid4())
        
        # Store token with expiration
        reset_tokens[email] = {
            "token": reset_token,
            "user_id": str(user.user_id),
            "expires": time.time() + 3600  # 1 hour
        }
        
        # Send email with reset link
        reset_link = f"{WEBAPP_URL}/reset-password/{reset_token}"
        send_reset_email(email, reset_link)
        
        return {"message": "If the email exists, a reset link has been sent"}, 200

@authenticate_ns.route('/reset-password')
class ResetPassword(Resource):
    @authenticate_ns.expect(reset_password_model)
    @authenticate_ns.response(200, "Password reset successful", auth_success_response)
    def post(self):
        """Reset password and issue new JWT"""
        data = request.json
        token = data.get("token")
        new_password = data.get("newPassword")
        
        # Find user by token
        user_id = None
        email = None
        for e, info in reset_tokens.items():
            if info["token"] == token and info["expires"] > time.time():
                user_id = info["user_id"]
                email = e
                break
                
        if not user_id:
            return {"error": "Invalid or expired token"}, 400
            
        # Update password
        auth = UserAuthenticate.query.filter_by(user_id=user_id).first()
        if not auth:
            return {"error": "User not found"}, 404
            
        auth.password_hashed = hash_password(new_password)
        db.session.commit()
        
        # Remove used token
        del reset_tokens[email]
        
        # Generate new JWT for automatic login
        new_jwt = generate_jwt_token(user_id)
        
        # Return success with new JWT
        return {
            "message": "Password reset successful",
            "userId": user_id,
            "token": new_jwt
        }, 200

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
            street_number=data.get('streetNumber').title(),
            street_name=data.get('streetName').title(),
            unit_number=data.get('unitNumber').title(),
            building_name=data.get('buildingName').title(),
            district=data.get('district').title(),
            city=data.get('city').title(),
            state_province=data.get('stateProvince').title(),
            postal_code=data.get('postalCode').title(),
            country=data.get('country').title()
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
        address.street_number = data.get('streetNumber', address.street_number).title()
        address.street_name = data.get('streetName', address.street_name).title()
        address.unit_number=data.get('unitNumber', address.unit_number).title()
        address.building_name=data.get('buildingName', address.building_name).title()
        address.district=data.get('district', address.district).title()
        address.city = data.get('city', address.city).title()
        address.state_province = data.get('stateProvince', address.state_province).title()
        address.postal_code = data.get('postalCode', address.postal_code).title()
        address.country = data.get('country', address.country).title()

        db.session.commit()
        return address

##### Seeding #####
# Provide seed data for test account with fixed values for replicability
def seed_data():
    try:
        # Fixed values for test account to ensure consistent testing
        TEST_USER_ID = uuid.UUID('a7c396e2-8370-4975-820e-c5ee8e3875c0')
        TEST_PASSWORD_HASH = '$2b$12$qHXz/XGhT57M.vltsTzoNOKVBDL2BHN0q0EEgXsNQ3lKD6rn3Y1eG'  # Corresponds to "test12345"
        
        # Check if test user already exists
        if UserAccount.query.filter_by(user_id=TEST_USER_ID).first() is None:
            # Add test account with fixed user_id
            test_user = UserAccount(
                user_id=TEST_USER_ID,  # Using fixed ID for consistent testing
                username="test",
                fullname="Test User",
                phone="12345678",
                email="test@test.com"
            )
            db.session.add(test_user)
            db.session.commit()
            
            # Create authentication with fixed password hash
            # Note: This hash corresponds to "test12345" and allows login with that password
            test_auth = UserAuthenticate(
                user_id=TEST_USER_ID,
                password_hashed=TEST_PASSWORD_HASH
            )
            db.session.add(test_auth)
            
            # Create address for test user
            test_address = UserAddress(
                user_id=TEST_USER_ID,
                street_number="Test",
                street_name="Test Street",
                unit_number="Test",
                building_name="Test Building",
                district="Test District",
                city="Test City",
                state_province="Test State",
                postal_code="Test123",
                country="Test Country"
            )
            db.session.add(test_address)
            db.session.commit()
            print("Test account created successfully with fixed user_id and password hash.")
        else:
            print("Test account already exists.")

    except IntegrityError as e:
        db.session.rollback()
        print(f"Data seeding failed due to integrity error: {e}")
    except Exception as e:
        db.session.rollback()
        print(f"Data seeding failed: {e}")


# Add name spaces into api
api.add_namespace(account_ns)
api.add_namespace(authenticate_ns)
api.add_namespace(address_ns)

if __name__ == '__main__':
    with app.app_context():
        seed_data()
    app.run(host='0.0.0.0', port=5000, debug=True)