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
API_ROOT = f'/{API_VERSION}/api/crypto'

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
    wallet_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(UUID(as_uuid=True), unique=True, nullable=False)

    # Relationships
    holdings = db.relationship('CryptoHolding', back_populates='wallet', cascade='all, delete-orphan')

#(2) stores all tokens to ever exist (can be created or deleted)
class CryptoToken(db.Model):
    __tablename__ = 'crypto_token'
    token_id = db.Column(db.String(10), primary_key=True, unique=True, nullable=False)
    token_name = db.Column(db.String(100), unique=True, nullable=False)

    # Relationships
    holding = db.relationship('CryptoHolding', back_populates='token', cascade='all, delete-orphan')

#(3) stores all crypto holding data (many wallets hold many crypto coins with actual and held balances)
class CryptoHolding(db.Model):
    __tablename__ = 'crypto_holding'
    holding_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    wallet_id = db.Column(UUID(as_uuid=True), db.ForeignKey('crypto_wallet.wallet_id', ondelete='CASCADE'), nullable=False)
    token_id = db.Column(db.String(10), db.ForeignKey('crypto_token.token_id', ondelete='CASCADE'), nullable=False)
    actual_balance = db.Column(db.Float, default=0.0, nullable=False)
    held_balance = db.Column(db.Float, default=0.0, nullable=False)
    updated_on = db.Column(db.DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    wallet = db.relationship('CryptoWallet', back_populates='holdings', uselist=False)
    token = db.relationship('CryptoToken')

##### API Models - flask restx API autodoc #####
# To use flask restx, you will have to define API models with their input types
# For all API models, add a comment to the top to signify its importance
# E.g. Input/Output One/Many user account

# GET /v1/api/crypto/holdings?walletId={walletId}&tokenId={tokenId}
# GET API model for viewing crypto holding
crypto_holding_retrieve_input = holding_ns.model('CryptoHoldingRetrieveInput', {
    'walletId': fields.String(required=True, description='The wallet ID associated with the holding'),
    'tokenId': fields.String(required=True, description='The token ID associated with the holding'),
})

# GET API response model for viewing crypto holding
crypto_holding_retrieve_output = holding_ns.model('CryptoHoldingRetrieveOutput', {
    'holdingId': fields.String(attribute='holding_id', required=True, description='The unique holding ID'),
    'walletId': fields.String(attribute='wallet_id', required=True, description='The wallet ID associated with the holding'),
    'tokenId': fields.String(attribute='token_id', required=True, description='The token ID associated with the holding'),
    'actualBalance': fields.String(attribute='actual_balance', required=True, description='The actual balance of the token under this holding'),
    'heldBalance': fields.String(attribute='held_balance', required=True, description='The held balance of the token under this holding that are being reserved until its respective orders are placed'),
    'updatedOn': fields.String(attribute='updated_on', required=True, description='String of the last time of update')
})

# POST /v1/api/crypto/holdings
# POST API model for creating crypto holding
crypto_holding_create_input = holding_ns.model('CryptoHoldingCreateInput', {
    'walletId': fields.String(required=True, description='The wallet ID associated with the holding'),
    'tokenId': fields.String(required=True, description='The token ID associated with the holding'),
    'changeType': fields.String(required=True, description='The change associated with the update (deduct/add)'),
    'amount': fields.String(required=True, description='The amount of token associated with the transaction'),
})

# POST API response model for creating crypto holding
crypto_holding_create_output = holding_ns.model('CryptoHoldingCreateOutput', {
    'holdingId': fields.String(attribute='holding_id', required=True, description='The unique holding ID'),
    'walletId': fields.String(attribute='wallet_id', required=True, description='The wallet ID associated with the holding'),
    'tokenId': fields.String(attribute='token_id', required=True, description='The token ID associated with the holding'),
    'actualBalance': fields.Float(attribute='actual_balance', required=True, description='The initial balance of the holding'),
    'heldBalance': fields.Float(attribute='held_balance', required=True, description='The held balance of the holding (should be 0 initially)'),
})

# POST /v1/api/crypto/holdings
# POST API model for updating crypto holding
crypto_holding_update_input = holding_ns.model('CryptoHoldingUpdateInput', {
    'walletId': fields.String(required=True, description='The wallet ID associated with the holding'),
    'tokenId': fields.String(required=True, description='The token ID associated with the holding'),
    'changeType': fields.String(required=True, description='The type of change (add or deduct)'),
    'amount': fields.Float(required=True, description='The amount of token to be added or deducted'),
})

# POST API response model for creating crypto holding
crypto_holding_update_output = holding_ns.model('CryptoHoldingUpdateOutput', {
    'status': fields.String(required=True, description='Success or failure message'),
    'message': fields.String(required=True, description='Detailed message about the update'),
})

##### API actions - flask restx API autodoc #####
# To use flask restx, you will also have to seperate the CRUD actions from the DB table classes

# GET /v1/api/holdings/{wallet}/{token_id}
@holding_ns.route('/<string:wallet_id>/<string:token_id>')
@holding_ns.param('wallet_id', 'The unique identifier of a wallet')
@holding_ns.param('token_id', 'The unique identifier of a token')
class CryptoHoldingResource(Resource):
    
    def get(self, wallet_id, token_id):
        """Retrieve the actual balance and held balance for a specific crypto holding"""
        
        # Query the CryptoHolding table to find the holding by wallet_id and token_id
        holding = CryptoHolding.query.filter_by(wallet_id=wallet_id, token_id=token_id).first()
        
        # If no holding is found, return a 404 error
        if not holding:
            holding_ns.abort(404, f"Holding for wallet {wallet_id} and token {token_id} not found")
        
        # Return the holding information (actual balance and held balance)
        return holding, 200

# POST /v1/api/holdings/held-balance that adds or deduct order amount to held-balance
@holding_ns.route('/held-balance')
class CryptoHoldingHeldBalanceResource(Resource):
    @holding_ns.expect(crypto_holding_update_input, validate=True)
    def post(self):
        """Update the held balance of a crypto holding"""
        data = request.json
        wallet_id = data.get('walletId')
        token_id = data.get('tokenId')
        change_type = data.get('changeType')
        amount = float(data.get('amount'))

        holding = CryptoHolding.query.filter_by(wallet_id=wallet_id, token_id=token_id).first()
        if not holding:
            holding_ns.abort(404, "Holding not found")

        if change_type == "add":
            holding.held_balance += amount
        elif change_type == "deduct":
            holding.held_balance -= amount
        else:
            holding_ns.abort(400, "Invalid changeType. Use 'add' or 'deduct'.")

        db.session.commit()
        return {"message": "Actual balance updated successfully"}

# POST /v1/api/holdings/actual-balance that adds or decreases order amount to actual-balance
@holding_ns.route('/actual-balance')
class CryptoHoldingActualBalanceResource(Resource):
    @holding_ns.expect(crypto_holding_update_input, validate=True)
    def post(self):
        """Update the actual balance of a crypto holding"""
        data = request.json
        wallet_id = data.get('walletId')
        token_id = data.get('tokenId')
        change_type = data.get('changeType')
        amount = float(data.get('amount'))

        holding = CryptoHolding.query.filter_by(wallet_id=wallet_id, token_id=token_id).first()
        if not holding:
            holding_ns.abort(404, "Holding not found")

        if change_type == "add":
            holding.actual_balance += amount
        elif change_type == "deduct":
            holding.actual_balance -= amount
        else:
            holding_ns.abort(400, "Invalid changeType. Use 'add' or 'deduct'.")

        db.session.commit()
        return {"message": "Actual balance updated successfully"}
    
# @token_ns.route('')
# class CryptoTokenListResource(Resource):
#     @token_ns.marshal_list_with(token_output_model)
#     def get(self):
#         """Fetch all crypto tokens"""
#         return CryptoToken.query.all()

# @token_ns.route('/<string:tokenTicker>')
# @token_ns.param('tokenTicker', 'The ticker symbol of a token')
# class CryptoTokenResource(Resource):
#     @token_ns.marshal_with(token_output_model)
#     def get(self, tokenTicker):
#         """Fetch a specific crypto token using tokenTicker as a path parameter"""
#         token = CryptoToken.query.get_or_404(tokenTicker, description='Token not found')
#         return token

#     @token_ns.expect(token_input_model, validate=True)
#     @token_ns.marshal_with(token_output_model, code=201)
#     def post(self, tokenTicker):
#         """Create a new crypto token"""
#         data = request.json
        
#         # Check if token with this ticker already exists
#         existing_token = CryptoToken.query.get(tokenTicker)
#         if existing_token:
#             token_ns.abort(400, 'Token with this ticker already exists')
            
#         new_token = CryptoToken(
#             token_ticker=tokenTicker
#         )
        
#         try:
#             db.session.add(new_token)
#             db.session.commit()
#             return new_token, 201
#         except IntegrityError:
#             db.session.rollback()
#             token_ns.abort(400, 'Token could not be created due to integrity error')

#     @token_ns.expect(token_input_model, validate=True)
#     @token_ns.marshal_with(token_output_model)
#     def put(self, tokenTicker):
#         """Update an existing crypto token"""
#         token = CryptoToken.query.get_or_404(tokenTicker, description='Token not found')
#         data = request.json
        
#         # Since token_ticker is the primary key, updating it would mean creating a new token
#         # and deleting the old one, which would affect all relationships.
#         # This is a complex operation that should be handled with care.
#         if data.get('tokenTicker') != tokenTicker:
#             token_ns.abort(400, 'Cannot modify token ticker as it is the primary key. Create a new token instead.')
        
#         try:
#             db.session.commit()
#             return token
#         except IntegrityError:
#             db.session.rollback()
#             token_ns.abort(400, 'Token could not be updated due to integrity error')

#     def delete(self, tokenTicker):
#         """Delete a crypto token"""
#         token = CryptoToken.query.get_or_404(tokenTicker, description='Token not found')
        
#         try:
#             db.session.delete(token)
#             db.session.commit()
#             return {'message': 'Token deleted successfully'}
#         except IntegrityError:
#             db.session.rollback()
#             token_ns.abort(400, 'Token could not be deleted due to integrity constraints')

# # CRUD for CryptoTrade
# @trade_ns.route('')
# class CryptoTradeListResource(Resource):
#     @trade_ns.marshal_list_with(trade_output_model)
#     def get(self):
#         """Fetch all crypto trades"""
#         return CryptoTrade.query.all()

# @trade_ns.route('/<uuid:walletId>')
# @trade_ns.param('walletId', 'The wallet ID to fetch trades for')
# class CryptoTradeUserResource(Resource):
#     @trade_ns.marshal_list_with(trade_output_model)
#     def get(self, walletId):
#         """Fetch all trades of a specific wallet using walletId as a path parameter"""
#         # Check if wallet exists
#         wallet = CryptoWallet.query.get_or_404(walletId, description='Wallet not found')
        
#         # Fetch all trades for the wallet
#         trades = CryptoTrade.query.filter_by(wallet_id=walletId).all()
#         return trades

# @trade_ns.route('/<uuid:tradeId>')
# @trade_ns.param('tradeId', 'The unique identifier of a trade')
# class CryptoTradeResource(Resource):
#     @trade_ns.marshal_with(trade_output_model)
#     def get(self, tradeId):
#         """Fetch a specific trade using tradeId as a path parameter"""
#         trade = CryptoTrade.query.get_or_404(tradeId, description='Trade not found')
#         return trade

#     @trade_ns.expect(trade_input_model, validate=True)
#     @trade_ns.marshal_with(trade_output_model, code=201)
#     def post(self, tradeId):
#         """Create a new trade"""
#         data = request.json
        
#         # Validate that wallet and token exist
#         wallet = CryptoWallet.query.get_or_404(data.get('walletId'), description='Wallet not found')
#         token = CryptoToken.query.get_or_404(data.get('tokenTicker'), description='Token not found')
        
#         new_trade = CryptoTrade(
#             trade_id=tradeId,
#             wallet_id=data.get('walletId'),
#             token_ticker=data.get('tokenTicker'),
#             amount=data.get('amount'),
#             price=data.get('price'),
#             trade_type=data.get('tradeType'),
#             status=data.get('status', 'completed')
#         )
        
#         try:
#             db.session.add(new_trade)
#             db.session.commit()
            
#             # Optionally update holdings after trade
#             # This would be implemented as a transaction
            
#             return new_trade, 201
#         except IntegrityError:
#             db.session.rollback()
#             trade_ns.abort(400, 'Trade could not be created due to integrity error')

#     @trade_ns.expect(trade_input_model, validate=True)
#     @trade_ns.marshal_with(trade_output_model)
#     def put(self, tradeId):
#         """Update an existing trade"""
#         trade = CryptoTrade.query.get_or_404(tradeId, description='Trade not found')
#         data = request.json
        
#         # Allow updating any field, but verify that referenced entities exist
#         if 'walletId' in data:
#             wallet = CryptoWallet.query.get_or_404(data.get('walletId'), description='Wallet not found')
#             trade.wallet_id = data.get('walletId')
            
#         if 'tokenTicker' in data:
#             token = CryptoToken.query.get_or_404(data.get('tokenTicker'), description='Token not found')
#             trade.token_ticker = data.get('tokenTicker')
        
#         trade.amount = data.get('amount', trade.amount)
#         trade.price = data.get('price', trade.price)
#         trade.trade_type = data.get('tradeType', trade.trade_type)
#         trade.status = data.get('status', trade.status)
        
#         try:
#             db.session.commit()
#             return trade
#         except IntegrityError:
#             db.session.rollback()
#             trade_ns.abort(400, 'Trade could not be updated due to integrity error')

#     def delete(self, tradeId):
#         """Delete a trade"""
#         trade = CryptoTrade.query.get_or_404(tradeId, description='Trade not found')
        
#         try:
#             db.session.delete(trade)
#             db.session.commit()
#             return {'message': 'Trade deleted successfully'}
#         except IntegrityError:
#             db.session.rollback()
#             trade_ns.abort(400, 'Trade could not be deleted due to integrity constraints')


##### Seeding #####
# Provide seed data for all tables
def seed_data():
    try:
        with open("seeddata.json", "r") as file:
            data = json.load(file)

        # 1) Insert CryptoWallet data
        crypto_wallets_data = data.get("cryptoWallets", [])
        existing_usernames = {u.user_id for u in CryptoWallet.query.all()}

        for wall in crypto_wallets_data:
            # Skip if user already exists
            if wall["userId"] in existing_usernames:
                print(f"Skipping user '{wall['userId']}' as it already exists.")
                continue

            new_wallet = CryptoWallet(
                user_id=wall["userId"], #gotta fake it for this one
                wallet_id=wall["walletId"],
            )
            db.session.add(new_wallet)
        db.session.commit()

        # 2) Insert CryptoToken data
        crypto_tokens_data = data.get("cryptoTokens", [])
        existing_tokens = {t.token_id for t in CryptoToken.query.all()}

        for token in crypto_tokens_data:
            # Skip if token already exists
            if token["token_id"] in existing_tokens:
                print(f"Skipping token '{token['token_id']}' as it already exists.")
                continue

            new_token = CryptoToken(
                token_id=token["token_id"],
                token_name=token["token_name"]
            )
            db.session.add(new_token)
        db.session.commit()

        # 3) Insert CryptoHolding data
        crypto_holdings_data = data.get("cryptoHoldings", [])
        # Creating a lookup for wallet_id and token_id
        wallet_lookup = {w.wallet_id: w for w in CryptoWallet.query.all()}
        token_lookup = {t.token_id: t for t in CryptoToken.query.all()}

        for holding in crypto_holdings_data:
            wallet_id = holding["walletId"]
            token_id = holding["tokenId"]

            # # Skip if wallet or token does not exist
            if wallet_id not in wallet_lookup:
                print(f"Skipping holding for unknown wallet '{wallet_id}'")
                continue
            if token_id not in token_lookup:
                print(f"Skipping holding for unknown token '{token_id}'")
                continue

            # Creating new CryptoHolding
            new_holding = CryptoHolding(
                holding_id=holding["holdingId"],  # Generate new unique UUID
                wallet_id=holding["walletId"],
                token_id=holding["tokenId"],
                actual_balance=holding["actualBalance"],
                held_balance=holding["heldBalance"],
                updated_on=holding["updatedOn"]
                # updated_on=datetime.fromisoformat(holding["updatedOn"].replace("Z", "+00:00"))
            )
            db.session.add(new_holding)
        db.session.commit()

    except IntegrityError as e:
        db.session.rollback()
        print(f"Data seeding failed due to integrity error: {e}")
    except FileNotFoundError:
        print("seeddata.json not found. Skipping seeding.")

# Add name spaces into api
api.add_namespace(token_ns)
api.add_namespace(wallet_ns)
api.add_namespace(holding_ns)

if __name__ == '__main__':
    with app.app_context():
        seed_data()
    app.run(host='0.0.0.0', port=5000, debug=True)