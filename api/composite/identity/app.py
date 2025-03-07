from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import requests
import bcrypt


##### Configuration #####
# Define API version and root path
API_VERSION = 'v1'
API_ROOT = f'/{API_VERSION}/api'

app = Flask(__name__)
CORS(app)

# Flask swagger (flask_restx) api documentation
# Creates API documentation automatically
blueprint = Blueprint('api',__name__,url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Identity Service API', description='Identity Service API for Yorkshire Crypto Exchange')

# Register Blueprint with Flask app
app.register_blueprint(blueprint)

# Environment variables for microservice
# Environment variables for microservice URLs
USERS_SERVICE_URL = "http://localhost:5003/v1/api/user"
FIAT_SERVICE_URL = "http://localhost:5001/v1/api/fiat"

# Define namespaces to group api calls together
# Namespaces are essentially folders that group all related API calls
identity_ns = Namespace('identity', description='Identity related operations')


##### API Models - flask restx API autodoc #####
# To use flask restx, you will have to define API models with their input types
# For all API models, add a comment to the top to signify its importance
# E.g. Input/Output One/Many user account

# Input one user account
create_account_model = api.model(
    "CreateAccount",
    {
        # Account fields
        "username": fields.String(required=True, description="Username"),
        "fullname": fields.String(required=True, description="Full Name"),
        "phone": fields.String(required=True, description="Phone Number"),
        "email": fields.String(required=True, description="Email Address"),

        # Authenticate fields
        "password": fields.String(required=True, description="User Password"),

        # Address fields
        'streetNumber': fields.String(attribute='street_number',required=True, description='The street number'),
        'streetName': fields.String(attribute='street_name',required=True, description='The street name'),

        # # Nullable fields inside address
        'unitNumber': fields.String(attribute='unit_number',required=False, description='The unit number'),
        'buildingName': fields.String(attribute='building_name',required=False, description='The building name'),
        'district': fields.String(attribute='district',required=False, description='The district'),

        'city': fields.String(required=True, description='The city'),
        'stateProvince': fields.String(attribute='state_province',required=True, description='The state or province'),
        'postalCode': fields.String(attribute='postal_code',required=True, description='The postal code'),
        'country': fields.String(required=True, description='The country')
    },
)

# Output given upon succesfuly creation of account
success_response = api.model(
    "SuccessResponse",
    {
        "message": fields.String(description="Success message"),
        "user_id": fields.String(description="Created User ID"),
    },
)

# Output given upon failure in general
error_response = api.model(
    "ErrorResponse",
    {
        "error": fields.String(description="Error message"),
        "details": fields.String(description="Error details"),
    },
)


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


##### API actions - flask restx API autodoc #####
# To use flask restx, you will also have to seperate the CRUD actions from the DB table classes

# Create account service
@identity_ns.route("/create-account")
class CreateAccount(Resource):
    @identity_ns.expect(create_account_model)
    @identity_ns.response(201, "User created successfully", success_response)
    @identity_ns.response(400, "Bad Request", error_response)
    @identity_ns.response(500, "Internal Server Error", error_response)
    def post(self):
        """Handles user account creation across microservices"""
        data = request.json

        username = data.get("username")
        password = data.get("password")
        fullname = data.get("fullname")
        phone = data.get("phone")
        email = data.get("email")

        # Address Fields
        street_number = data.get("streetNumber")
        street_name = data.get("streetName")
        unit_number = data.get("unitNumber")
        building_name = data.get("buildingName")
        district = data.get("district")
        city = data.get("city")
        state_province = data.get("stateProvince")
        postal_code = data.get("postalCode")
        country = data.get("country")

        # ✅ Fix 1: Validate required fields properly
        required_fields = [username, password, fullname, phone, email, country, street_number, street_name, city, state_province, postal_code]
        if None in required_fields or "" in required_fields:
            return {"error": "Missing required fields"}, 400  # Bad request response

        # ✅ Fix 2: Hash the password before storing it
        password_hashed = hash_password(password)

        # ✅ Fix 3: Create the user in account under user microservice
        user_account_payload = {
            "username": username,
            "fullname": fullname,
            "phone": phone,
            "email": email,
        }

        try:
            user_response = requests.post(f"{USERS_SERVICE_URL}/account", json=user_account_payload)
            if user_response.status_code != 201:
                return {
                    "error": "Failed to create user account",
                    "details": user_response.json() if user_response.content else "No response content"
                }, user_response.status_code
            user_data = user_response.json()
        except requests.RequestException as e:
            return {"error": "Failed to connect to user service", "details": str(e)}, 500

        user_id = user_data.get("userId")

        # ✅ Fix 4: Ensure user_id is retrieved correctly
        if not user_id:
            return {"error": "User ID missing from response"}, 500

        # ✅ Fix 5: Store authentication details in authenticate under users microservice
        user_auth_payload = {
            "passwordHashed": password_hashed
        }

        try:
            auth_response = requests.post(f"{USERS_SERVICE_URL}/authenticate/{user_id}", json=user_auth_payload)
            if auth_response.status_code != 201:
                return {
                    "error": "Failed to create authentication record",
                    "details": auth_response.json() if auth_response.content else "No response content"
                }, auth_response.status_code
        except requests.RequestException as e:
            return {"error": "Failed to connect to authentication service", "details": str(e)}, 500

        # ✅ Fix 6: Store address details in address under user microservice
        user_address_payload = {
            "streetNumber": street_number,
            "streetName": street_name,
            "unitNumber": unit_number,
            "buildingName": building_name,
            "district": district,
            "city": city,
            "stateProvince": state_province,
            "postalCode": postal_code,
            "country": country
        }

        try:
            address_response = requests.post(f"{USERS_SERVICE_URL}/address/{user_id}", json=user_address_payload)
            if address_response.status_code != 201:
                return {
                    "error": "Failed to store user address",
                    "details": address_response.json() if address_response.content else "No response content"
                }, address_response.status_code
        except requests.RequestException as e:
            return {"error": "Failed to connect to address service", "details": str(e)}, 500

        return {"message": "User account successfully created", "user_id": user_id}, 201

# Add name spaces into api
api.add_namespace(identity_ns)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)	