from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
import requests


##### Configuration #####
# Define API version and root path
API_VERSION = 'v1'
API_ROOT = f'/api/{API_VERSION}'

app = Flask(__name__)
CORS(app)

# Flask swagger (flask_restx) api documentation
# Creates API documentation automatically
blueprint = Blueprint('api',__name__,url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Order Management Service API', description='Order Management Service API for Yorkshire Crypto Exchange')

# Register Blueprint with Flask app
app.register_blueprint(blueprint)

# Environment variables for microservice
# Environment variables for microservice URLs
# NOTE: Do not use localhost here as localhost refer to this container itself
USERS_SERVICE_URL = "http://user-service:5000/api/v1/user"
FIAT_SERVICE_URL = "http://fiat-service:5000/api/v1/fiat"
CRYPTO_SERVICE_URL = "http://crypto-service:5000/api/v1/crypto"

# Define namespaces to group api calls together
# Namespaces are essentially folders that group all related API calls
order_ns = Namespace('order', description='Order related operations')

##### API Models - flask restx API autodoc #####
# To use flask restx, you will have to define API models with their input types
# For all API models, add a comment to the top to signify its importance
# E.g. Input/Output One/Many user account

# Input one user account - order request
create_account_model = order_ns.model(
    "CreateAccount",
    {
        # Admin details
        "userId": fields.String(required=True, description="User ID"),

        # Order details
        "fromTokenId": fields.String(required=True, description="Token ID of quote currency"),
        "fromAmount": fields.Float(required=True, description="Total amount of quote currency"),

        "toTokenId": fields.String(required=True, description="Token ID of base currency"),
        "toAmount": fields.Float(required=True, description="Total amount of base currency"),
        "limitPrice": fields.Float(required=True, description="Base price at which user is willing to execute"),

        "usdtFee": fields.Float(required=True, description="Fee of transaction"),
        "orderType": fields.Float(required=True, description="Type of Order (Limit/Market)")
    },
)

# Output given upon successful creation of order in transaction log
success_creation_response = order_ns.model(
    "SuccessResponse",
    {
        "message": fields.String(description="Success message"),
        "transactionId": fields.String(attribute='transaction_id', description="Created Transaction ID"),
    },
)

# Output given upon successful update of order in transaction log
success_update_response = order_ns.model(
    "SuccessResponse",
    {
        "message": fields.String(description="Success message"),
        "transactionId": fields.String(attribute='transaction_id', description="Updated Transaction ID"),
    },
)

# Output given upon failure in general
error_response = order_ns.model(
    "ErrorResponse",
    {
        "error": fields.String(description="Error message"),
        "details": fields.String(description="Error details"),
    },
)

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

        # # Address Fields
        # street_number = data.get("streetNumber")
        # street_name = data.get("streetName")
        # unit_number = data.get("unitNumber")
        # building_name = data.get("buildingName")
        # district = data.get("district")
        # city = data.get("city")
        # state_province = data.get("stateProvince")
        # postal_code = data.get("postalCode")
        # country = data.get("country")

        # Validate required fields properly
        # required_fields = [username, password, fullname, phone, email, country, street_number, street_name, city, state_province, postal_code]
        required_fields = [username, password, fullname, phone, email]
        if None in required_fields or "" in required_fields:
            return {"error": "Missing required fields"}, 400  # Bad request response

        # Create the user in account under user microservice
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

        # Ensure user_id is retrieved correctly
        if not user_id:
            return {"error": "User ID missing from response"}, 500

        # Store authentication details in authenticate under users microservice
        user_auth_payload = {
            "password": password
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

        # # Store address details in address under user microservice
        # user_address_payload = {
        #     "streetNumber": street_number,
        #     "streetName": street_name,
        #     "unitNumber": unit_number,
        #     "buildingName": building_name,
        #     "district": district,
        #     "city": city,
        #     "stateProvince": state_province,
        #     "postalCode": postal_code,
        #     "country": country
        # }

        # try:
        #     address_response = requests.post(f"{USERS_SERVICE_URL}/address/{user_id}", json=user_address_payload)
        #     if address_response.status_code != 201:
        #         return {
        #             "error": "Failed to store user address",
        #             "details": address_response.json() if address_response.content else "No response content"
        #         }, address_response.status_code
        # except requests.RequestException as e:
        #     return {"error": "Failed to connect to address service", "details": str(e)}, 500

        # Create fiat wallet using fiat microservice

        # Create crypto wallet using crypto microservice

        return {"message": "User account successfully created", "user_id": user_id}, 201

# Add name spaces into api
api.add_namespace(identity_ns)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)	