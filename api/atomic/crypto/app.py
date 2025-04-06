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
import datetime

##### Configuration #####
# Define API version and root path
API_VERSION = 'v1'
API_ROOT = f'/api/{API_VERSION}/crypto'

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

DB_NAME = os.getenv("DB_NAME", "crypto_db")
DB_USER = os.getenv("DB_USER", "user")
DB_PASS = os.getenv("DB_PASS", "password")

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask swagger (flask_restx) api documentation
# Creates API documentation automatically
blueprint = Blueprint('api',__name__,url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Crypto API', description='Crypto API for Yorkshire Crypto Exchange')

# Register Blueprint with Flask app
app.register_blueprint(blueprint)

# Define namespaces to group api calls together
# Namespaces are essentially folders that group all APIs calls related to a table
# You can treat it as table_ns
# Its essential that you use this at your routes
token_ns = Namespace('token', description='Token related operations')
wallet_ns = Namespace('wallet', description='Wallet related operations')
holding_ns = Namespace('holdings', description='Holding related operations')

##### DB table classes declaration - flask migrate #####
# To use flask migrate, you have to create classes for the table of the entity
# Use these classes to define their data type, uniqueness, nullability, and relationships
# This will auto generate migration code for the database, removing the need for us to manually code SQL to initialise database
# Separate the CRUD functions outside of the classes. Better for separation of concern.

class CryptoWallet(db.Model):
    __tablename__ = 'crypto_wallet'
    user_id = db.Column(db.String(100), primary_key = True, unique=True, nullable=False)

#(2) stores all tokens to ever exist (can be created or deleted)
class CryptoToken(db.Model):
    __tablename__ = 'crypto_token'
    token_id = db.Column(db.String(15), primary_key=True, unique=True, nullable=False)
    token_name = db.Column(db.String(100), unique=True, nullable=False)
    created = db.Column(db.DateTime(timezone=True), server_default=func.now())

#(3) stores all crypto holding data (many wallets hold many crypto coins with actual and available balances)
class CryptoHolding(db.Model):
    __tablename__ = 'crypto_holding'
    user_id = db.Column(db.String(100), primary_key = True, nullable=False)
    token_id = db.Column(db.String(15), primary_key = True, nullable=False)
    actual_balance = db.Column(db.Float, default=0.0, nullable=False)
    available_balance = db.Column(db.Float, default=0.0, nullable=False)
    updated_on = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

##### API Models - flask restx API autodoc #####
# To use flask restx, you will have to define API models with their input types
# For all API models, add a comment to the top to signify its importance
# E.g. Input/Output One/Many user account

# CryptoWallet API Models
wallet_output_model = wallet_ns.model('CryptoWalletOutput', {
    'userId': fields.String(attribute='user_id', required=True, description='The unique user ID')
})

wallet_input_model = wallet_ns.model('CryptoWalletInput', {
    'userId': fields.String(attribute='user_id', required=True, description='The unique user ID')
})

# CryptoToken API Models
token_output_model = token_ns.model('CryptoTokenOutput', {
    'tokenId': fields.String(attribute='token_id', required=True, description='The unique token ID'),
    'tokenName': fields.String(attribute='token_name', required=True, description='The name of the token'),
    'created': fields.DateTime(description='When the token was created')
})

token_input_model = token_ns.model('CryptoTokenInput', {
    'tokenId': fields.String(attribute='token_id', required=True, description='The unique token ID'),
    'tokenName': fields.String(attribute='token_name', required=True, description='The name of the token')
})

# For PUT operations on tokens (no tokenId needed since it's in the path)
token_update_model = token_ns.model('CryptoTokenUpdate', {
    'tokenName': fields.String(attribute='token_name', required=True, description='The name of the token')
})

# CryptoHolding API Models
holding_output_model = holding_ns.model('CryptoHoldingOutput', {
    'userId': fields.String(attribute='user_id', required=True, description='The user ID associated with the holding'),
    'tokenId': fields.String(attribute='token_id', required=True, description='The token ID associated with the holding'),
    'actualBalance': fields.Float(attribute='actual_balance', required=True, description='The actual balance of the token'),
    'availableBalance': fields.Float(attribute='available_balance', required=True, description='The available balance of the token (reserved for orders)'),
    'updatedOn': fields.DateTime(attribute='updated_on', description='When the holding was last updated')
})

holding_input_model = holding_ns.model('CryptoHoldingInput', {
    'userId': fields.String(attribute='user_id', required=True, description='The user ID associated with the holding'),
    'tokenId': fields.String(attribute='token_id', required=True, description='The token ID associated with the holding'),
    'actualBalance': fields.Float(attribute='actual_balance', required=True, description='The actual balance of the token'),
    'availableBalance': fields.Float(attribute='available_balance', required=True, description='The available balance of the token (reserved for orders)')
})

# Model for updating holdings (only non-primary key fields can be updated)
holding_update_model = holding_ns.model('CryptoHoldingUpdate', {
    'actualBalance': fields.Float(attribute='actual_balance', required=False, description='The new actual balance of the token'),
    'availableBalance': fields.Float(attribute='available_balance', required=False, description='The new available balance of the token')
})

# Updated model for operations that change amounts - now including userId and tokenId
amount_change_model = holding_ns.model('CryptoAmountChange', {
    'userId': fields.String(required=True, description='The user ID associated with the holding'),
    'tokenId': fields.String(required=True, description='The token ID associated with the holding'),
    'amountChanged': fields.Float(required=True, description='The amount to add or subtract')
})

##### API actions - flask restx API autodoc #####
# To use flask restx, you will also have to seperate the CRUD actions from the DB table classes

# CryptoWallet Routes
@wallet_ns.route('')
class CryptoWalletList(Resource):
    @wallet_ns.marshal_list_with(wallet_output_model)
    def get(self):
        """Get all crypto wallets"""
        return CryptoWallet.query.all()
    
    @wallet_ns.expect(wallet_input_model, validate=True)
    @wallet_ns.marshal_with(wallet_output_model, code=201)
    def post(self):
        """Create a new crypto wallet"""
        data = request.json
        
        # Check if wallet already exists for user
        existing_wallet = CryptoWallet.query.filter_by(user_id=data['userId']).first()
        if existing_wallet:
            wallet_ns.abort(400, f"Wallet already exists for user ID: {data['userId']}")
        
        new_wallet = CryptoWallet(
            user_id=data['userId']
        )
        
        try:
            db.session.add(new_wallet)
            db.session.commit()
            return new_wallet, 201
        except Exception as e:
            db.session.rollback()
            wallet_ns.abort(400, f"Failed to create wallet: {str(e)}")

@wallet_ns.route('/<string:userId>')
@wallet_ns.param('userId', 'The unique user ID')
class CryptoWalletResource(Resource):
    @wallet_ns.marshal_with(wallet_output_model)
    def get(self, userId):
        """Get a crypto wallet by user ID"""
        return CryptoWallet.query.get_or_404(userId)
    
    def delete(self, userId):
        """Delete a crypto wallet and all associated holdings"""
        wallet = CryptoWallet.query.get_or_404(userId)
        
        try:
            # First delete all holdings for this user
            holdings = CryptoHolding.query.filter_by(user_id=userId).all()
            for holding in holdings:
                db.session.delete(holding)
            
            # Then delete the wallet
            db.session.delete(wallet)
            db.session.commit()
            return {'message': f'Wallet for user ID {userId} and all associated holdings deleted successfully'}, 200
        except Exception as e:
            db.session.rollback()
            wallet_ns.abort(400, f"Failed to delete wallet: {str(e)}")

# CryptoToken Routes
@token_ns.route('')
class CryptoTokenList(Resource):
    @token_ns.marshal_list_with(token_output_model)
    def get(self):
        """Get all crypto tokens"""
        return CryptoToken.query.all()
    
    @token_ns.expect(token_input_model, validate=True)
    @token_ns.marshal_with(token_output_model, code=201)
    def post(self):
        """Create a new crypto token"""
        data = request.json
        
        # Check if token already exists
        existing_token = CryptoToken.query.filter_by(token_id=data['tokenId']).first()
        if existing_token:
            token_ns.abort(400, f"Token with ID {data['tokenId']} already exists")
        
        new_token = CryptoToken(
            token_id=data['tokenId'],
            token_name=data['tokenName']
        )
        
        try:
            db.session.add(new_token)
            db.session.commit()
            return new_token, 201
        except Exception as e:
            db.session.rollback()
            token_ns.abort(400, f"Failed to create token: {str(e)}")

@token_ns.route('/<string:tokenId>')
@token_ns.param('tokenId', 'The unique token ID')
class CryptoTokenResource(Resource):
    @token_ns.marshal_with(token_output_model)
    def get(self, tokenId):
        """Get a crypto token by ID"""
        return CryptoToken.query.get_or_404(tokenId)
    
    @token_ns.expect(token_update_model, validate=True)
    @token_ns.marshal_with(token_output_model)
    def put(self, tokenId):
        """Update a crypto token (only name can be updated, ID cannot be changed)"""
        token = CryptoToken.query.get_or_404(tokenId)
        data = request.json
        
        if 'tokenName' in data:
            token.token_name = data['tokenName']
        
        try:
            db.session.commit()
            return token, 200
        except Exception as e:
            db.session.rollback()
            token_ns.abort(400, f"Failed to update token: {str(e)}")
    
    def delete(self, tokenId):
        """Delete a crypto token"""
        token = CryptoToken.query.get_or_404(tokenId)
        
        try:
            db.session.delete(token)
            db.session.commit()
            return {'message': f'Token {tokenId} deleted successfully'}, 200
        except Exception as e:
            db.session.rollback()
            token_ns.abort(400, f"Failed to delete token: {str(e)}")

# CryptoHolding Routes
@holding_ns.route('')
class CryptoHoldingList(Resource):
    @holding_ns.marshal_list_with(holding_output_model)
    def get(self):
        """Get all crypto holdings"""
        return CryptoHolding.query.all()
    
    @holding_ns.expect(holding_input_model, validate=True)
    @holding_ns.marshal_with(holding_output_model, code=201)
    def post(self):
        """Create a new crypto holding"""
        data = request.json
        
        # Check if user and token exist
        wallet = CryptoWallet.query.get_or_404(data['userId'], 'Wallet not found for user')
        token = CryptoToken.query.get_or_404(data['tokenId'], 'Token not found')
        
        # Check if holding already exists
        existing_holding = CryptoHolding.query.filter_by(
            user_id=data['userId'],
            token_id=data['tokenId']
        ).first()
        
        if existing_holding:
            holding_ns.abort(400, f"Holding already exists for user {data['userId']} and token {data['tokenId']}")
        
        new_holding = CryptoHolding(
            user_id=data['userId'],
            token_id=data['tokenId'],
            actual_balance=data.get('actualBalance', 0.0),
            available_balance=data.get('availableBalance', 0.0)
        )
        
        try:
            db.session.add(new_holding)
            db.session.commit()
            return new_holding, 201
        except Exception as e:
            db.session.rollback()
            holding_ns.abort(400, f"Failed to create holding: {str(e)}")

# New route to get all holdings for a specific user
@holding_ns.route('/<string:userId>')
@holding_ns.param('userId', 'The user ID')
class UserCryptoHoldingList(Resource):
    @holding_ns.marshal_list_with(holding_output_model)
    def get(self, userId):
        """Get all crypto holdings for a specific user"""
        # Check if user exists
        wallet = CryptoWallet.query.get_or_404(userId, f'Wallet not found for user {userId}')
        
        # Get all holdings for this user
        holdings = CryptoHolding.query.filter_by(user_id=userId).all()
        
        return holdings

@holding_ns.route('/<string:userId>/<string:tokenId>')
@holding_ns.param('userId', 'The user ID')
@holding_ns.param('tokenId', 'The token ID')
class CryptoHoldingResource(Resource):
    @holding_ns.marshal_with(holding_output_model)
    def get(self, userId, tokenId):
        """Get a crypto holding by user ID and token ID"""
        holding = CryptoHolding.query.filter_by(user_id=userId, token_id=tokenId).first_or_404(
            description=f'Holding not found for user {userId} and token {tokenId}'
        )
        return holding
    
    @holding_ns.expect(holding_update_model, validate=True)
    @holding_ns.marshal_with(holding_output_model)
    def put(self, userId, tokenId):
        """Update a crypto holding with new values"""
        holding = CryptoHolding.query.filter_by(user_id=userId, token_id=tokenId).first_or_404(
            description=f'Holding not found for user {userId} and token {tokenId}'
        )
        
        data = request.json
        
        # Update only fields that were provided in the request
        if 'actualBalance' in data:
            holding.actual_balance = data['actualBalance']
        
        if 'availableBalance' in data:
            holding.available_balance = data['availableBalance']
        
        try:
            db.session.commit()
            return holding, 200
        except Exception as e:
            db.session.rollback()
            holding_ns.abort(400, f"Failed to update holding: {str(e)}")
    
    def delete(self, userId, tokenId):
        """Delete a crypto holding"""
        holding = CryptoHolding.query.filter_by(user_id=userId, token_id=tokenId).first_or_404(
            description=f'Holding not found for user {userId} and token {tokenId}'
        )
        
        try:
            db.session.delete(holding)
            db.session.commit()
            return {'message': f'Holding for user {userId} and token {tokenId} deleted successfully'}, 200
        except Exception as e:
            db.session.rollback()
            holding_ns.abort(400, f"Failed to delete holding: {str(e)}")

# Specialized routes for different holding update operations - UPDATED to use request body instead of query params
@holding_ns.route('/deposit')
class CryptoHoldingDeposit(Resource):
    @holding_ns.expect(amount_change_model, validate=True)
    def post(self):
        """Deposit tokens to both actual and available balance"""
        data = request.json
        userId = data.get('userId')
        tokenId = data.get('tokenId')
        amountChanged = data.get('amountChanged', 0.0)
        
        if not userId or not tokenId:
            holding_ns.abort(400, "userId and tokenId are required in the request body")
        
        if amountChanged <= 0:
            holding_ns.abort(400, "amountChanged must be positive for deposits")
        
        holding = CryptoHolding.query.filter_by(user_id=userId, token_id=tokenId).first()
        
        if not holding:
            # Create new holding if it doesn't exist
            wallet = CryptoWallet.query.get_or_404(userId, 'Wallet not found for user')
            token = CryptoToken.query.get_or_404(tokenId, 'Token not found')
            
            holding = CryptoHolding(
                user_id=userId,
                token_id=tokenId,
                actual_balance=amountChanged,
                available_balance=amountChanged
            )
            db.session.add(holding)
        else:
            # Update existing holding
            holding.actual_balance += amountChanged
            holding.available_balance += amountChanged
        
        try:
            db.session.commit()
            return {
                'message': f'Successfully deposited {amountChanged} tokens',
                'userId': userId,
                'tokenId': tokenId,
                'actualBalance': holding.actual_balance,
                'availableBalance': holding.available_balance
            }, 200
        except Exception as e:
            db.session.rollback()
            holding_ns.abort(400, f"Failed to deposit tokens: {str(e)}")

@holding_ns.route('/reserve')
class CryptoHoldingReserve(Resource):
    @holding_ns.expect(amount_change_model, validate=True)
    def post(self):
        """Reserve tokens for an order (reduces available balance only)"""
        data = request.json
        userId = data.get('userId')
        tokenId = data.get('tokenId')
        amountChanged = data.get('amountChanged', 0.0)
        
        if not userId or not tokenId:
            holding_ns.abort(400, "userId and tokenId are required in the request body")
        
        if amountChanged <= 0:
            holding_ns.abort(400, "amountChanged must be positive for reserving tokens")
        
        holding = CryptoHolding.query.filter_by(user_id=userId, token_id=tokenId).first_or_404(
            description=f'Holding not found for user {userId} and token {tokenId}'
        )
        
        # Check if sufficient available balance
        if holding.available_balance < amountChanged:
            holding_ns.abort(400, f"Insufficient available balance. Required: {amountChanged}, Available: {holding.available_balance}")
        
        holding.available_balance -= amountChanged
        
        try:
            db.session.commit()
            return {
                'message': f'Successfully reserved {amountChanged} tokens',
                'userId': userId,
                'tokenId': tokenId,
                'actualBalance': holding.actual_balance,
                'availableBalance': holding.available_balance
            }, 200
        except Exception as e:
            db.session.rollback()
            holding_ns.abort(400, f"Failed to reserve tokens: {str(e)}")

@holding_ns.route('/release')
class CryptoHoldingRelease(Resource):
    @holding_ns.expect(amount_change_model, validate=True)
    def post(self):
        """Release reserved tokens (increases available balance only)"""
        data = request.json
        userId = data.get('userId')
        tokenId = data.get('tokenId')
        amountChanged = data.get('amountChanged', 0.0)
        
        if not userId or not tokenId:
            holding_ns.abort(400, "userId and tokenId are required in the request body")
        
        if amountChanged <= 0:
            holding_ns.abort(400, "amountChanged must be positive for releasing tokens")
        
        holding = CryptoHolding.query.filter_by(user_id=userId, token_id=tokenId).first_or_404(
            description=f'Holding not found for user {userId} and token {tokenId}'
        )
        
        holding.available_balance += amountChanged
        
        try:
            db.session.commit()
            return {
                'message': f'Successfully released {amountChanged} tokens',
                'userId': userId,
                'tokenId': tokenId,
                'actualBalance': holding.actual_balance,
                'availableBalance': holding.available_balance
            }, 200
        except Exception as e:
            db.session.rollback()
            holding_ns.abort(400, f"Failed to release tokens: {str(e)}")

@holding_ns.route('/execute')
class CryptoHoldingExecute(Resource):
    @holding_ns.expect(amount_change_model, validate=True)
    def post(self):
        """Execute an order (reduces actual balance only)"""
        data = request.json
        userId = data.get('userId')
        tokenId = data.get('tokenId')
        amountChanged = data.get('amountChanged', 0.0)
        
        if not userId or not tokenId:
            holding_ns.abort(400, "userId and tokenId are required in the request body")
        
        if amountChanged <= 0:
            holding_ns.abort(400, "amountChanged must be positive for executing orders")
        
        holding = CryptoHolding.query.filter_by(user_id=userId, token_id=tokenId).first_or_404(
            description=f'Holding not found for user {userId} and token {tokenId}'
        )
        
        # Check if sufficient actual balance
        if holding.actual_balance < amountChanged:
            holding_ns.abort(400, f"Insufficient actual balance. Required: {amountChanged}, Available: {holding.actual_balance}")
        
        holding.actual_balance -= amountChanged
        
        try:
            db.session.commit()
            return {
                'message': f'Successfully executed order for {amountChanged} tokens',
                'userId': userId,
                'tokenId': tokenId,
                'actualBalance': holding.actual_balance,
                'availableBalance': holding.available_balance
            }, 200
        except Exception as e:
            db.session.rollback()
            holding_ns.abort(400, f"Failed to execute order: {str(e)}")

@holding_ns.route('/withdraw')
class CryptoHoldingWithdraw(Resource):
    @holding_ns.expect(amount_change_model, validate=True)
    def post(self):
        """Withdraw tokens (reduces both actual and available balance)"""
        data = request.json
        userId = data.get('userId')
        tokenId = data.get('tokenId')
        amountChanged = data.get('amountChanged', 0.0)
        
        if not userId or not tokenId:
            holding_ns.abort(400, "userId and tokenId are required in the request body")
        
        if amountChanged <= 0:
            holding_ns.abort(400, "amountChanged must be positive for withdrawals")
        
        holding = CryptoHolding.query.filter_by(user_id=userId, token_id=tokenId).first_or_404(
            description=f'Holding not found for user {userId} and token {tokenId}'
        )
        
        # Check if sufficient balances
        if holding.actual_balance < amountChanged:
            holding_ns.abort(400, f"Insufficient actual balance. Required: {amountChanged}, Available: {holding.actual_balance}")
        
        if holding.available_balance < amountChanged:
            holding_ns.abort(400, f"Insufficient available balance. Required: {amountChanged}, Available: {holding.available_balance}")
        
        holding.actual_balance -= amountChanged
        holding.available_balance -= amountChanged
        
        try:
            db.session.commit()
            return {
                'message': f'Successfully withdrew {amountChanged} tokens',
                'userId': userId,
                'tokenId': tokenId,
                'actualBalance': holding.actual_balance,
                'availableBalance': holding.available_balance
            }, 200
        except Exception as e:
            db.session.rollback()
            holding_ns.abort(400, f"Failed to withdraw tokens: {str(e)}")

# ##### Seeding #####
# # Provide seed data for all tables
# def seed_data():
#     try:
#         with open("seeddata.json", "r") as file:
#             data = json.load(file)

#         # 1) Insert CryptoWallet data
#         crypto_wallets_data = data.get("cryptoWallets", [])
#         existing_usernames = {u.user_id for u in CryptoWallet.query.all()}

#         for wall in crypto_wallets_data:
#             # Skip if user already exists
#             if wall["userId"] in existing_usernames:
#                 print(f"Skipping user '{wall['userId']}' as it already exists.")
#                 continue

#             new_wallet = CryptoWallet(
#                 user_id=wall["userId"], #gotta fake it for this one
#                 wallet_id=wall["walletId"],
#             )
#             db.session.add(new_wallet)
#         db.session.commit()

#         # 2) Insert CryptoToken data
#         crypto_tokens_data = data.get("cryptoTokens", [])
#         existing_tokens = {t.token_id for t in CryptoToken.query.all()}

#         for token in crypto_tokens_data:
#             # Skip if token already exists
#             if token["token_id"] in existing_tokens:
#                 print(f"Skipping token '{token['token_id']}' as it already exists.")
#                 continue

#             new_token = CryptoToken(
#                 token_id=token["token_id"],
#                 token_name=token["token_name"]
#             )
#             db.session.add(new_token)
#         db.session.commit()

#         # 3) Insert CryptoHolding data
#         crypto_holdings_data = data.get("cryptoHoldings", [])
#         # Creating a lookup for wallet_id and token_id
#         wallet_lookup = {w.wallet_id: w for w in CryptoWallet.query.all()}
#         token_lookup = {t.token_id: t for t in CryptoToken.query.all()}

#         for holding in crypto_holdings_data:
#             wallet_id = holding["walletId"]
#             token_id = holding["tokenId"]

#             # Skip if wallet or token does not exist
#             if wallet_id not in wallet_lookup:
#                 print(f"Skipping holding for unknown wallet '{wallet_id}'")
#                 continue
#             if token_id not in token_lookup:
#                 print(f"Skipping holding for unknown token '{token_id}'")
#                 continue

#             # Creating new CryptoHolding
#             new_holding = CryptoHolding(
#                 wallet_id=wallet_lookup[wallet_id].wallet_id,
#                 token_id=token_lookup[token_id].token_id,
#                 actual_balance=holding["actualBalance"],
#                 available_balance=holding["availableBalance"],
#                 updated_on=holding["updatedOn"]
#             )
#             db.session.add(new_holding)
#         db.session.commit()

#         print("Seed data successfully loaded from seeddata.json.")

#     except IntegrityError as e:
#         db.session.rollback()
#         print(f"Data seeding failed due to integrity error: {e}")
#     except FileNotFoundError:
#         print("seeddata.json not found. Skipping seeding.")

# Add name spaces into api
api.add_namespace(token_ns)
api.add_namespace(wallet_ns)
api.add_namespace(holding_ns)

if __name__ == '__main__':
    # with app.app_context():
    #     seed_data()
    app.run(host='0.0.0.0', port=5000, debug=True)