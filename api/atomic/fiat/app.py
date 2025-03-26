from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from werkzeug.exceptions import HTTPException
import json
import uuid
import os

##### Configuration #####
API_VERSION = 'v1'
API_ROOT = f'/{API_VERSION}/api/fiat'

app = Flask(__name__)
CORS(app)

# Detect if running inside Docker
RUNNING_IN_DOCKER = os.getenv("RUNNING_IN_DOCKER", "false").lower() == "true"

# Set Database Configuration Dynamically
if RUNNING_IN_DOCKER:
    DB_HOST = "postgres"   # Docker network name
    DB_PORT = "5432"
else:
    DB_HOST = "localhost"  # Local environment
    DB_PORT = "5433"

DB_NAME = os.getenv("DB_NAME", "fiat_db")
DB_USER = os.getenv("DB_USER", "user")
DB_PASS = os.getenv("DB_PASS", "password")

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

blueprint = Blueprint('api', __name__, url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Fiat API', description='Fiat API for Yorkshire Crypto Exchange')
app.register_blueprint(blueprint)

# Custom error handler for more informative 500 errors
@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({'error': e.description}), e.code
    return jsonify({'error': str(e)}), 500

##### Namespaces #####
currency_ns = Namespace('currency', description='Fiat currency operations')
account_ns = Namespace('account', description='Fiat account operations')

##### DB table classes declaration - flask migrate #####
# To use flask migrate, you have to create classes for the table of the entity
# Use these classes to define their data type, uniqueness, nullability, and relationships
# This will auto generate migration code for the database, removing the need for us to manually code SQL to initialise database
# Separate the CRUD functions outside of the classes. Better for separation of concern.
class FiatCurrency(db.Model):
    __tablename__ = 'fiat_currency'
    currency_code = db.Column(db.String(3), primary_key=True)
    rate = db.Column(db.Numeric(18, 8), nullable=False)
    updated = db.Column(db.DateTime(timezone=True), server_default=func.now())


class FiatAccount(db.Model):
    __tablename__ = 'fiat_account'
    user_id = db.Column(
        db.String(100),
        primary_key=True
    )
    balance = db.Column(db.Numeric(18, 8), nullable=False, default=0.0)
    currency_code = db.Column(
        db.String(3),
        db.ForeignKey('fiat_currency.currency_code'),
        primary_key=True,
        nullable=False
    )
    updated = db.Column(db.DateTime(timezone=True), server_default=func.now())

##### API Models - flask restx API autodoc #####
# To use flask restx, you will have to define API models with their input types
# For all API models, add a comment to the top to signify its importance
# E.g. Input/Output One/Many user account

# Currency Models
fiat_currency_output_model = currency_ns.model('FiatCurrencyOutput', {
    'currency_code': fields.String(required=True),
    'rate': fields.Float(required=True),
    'updated': fields.DateTime
})

fiat_currency_input_model = currency_ns.model('FiatCurrencyInput', {
    'currency_code': fields.String(required=True),
    'rate': fields.Float(required=True)
})

fiat_currency_update_model = currency_ns.model('FiatCurrencyUpdate', {
    'rate': fields.Float(required=True)
})

# Account Models
fiat_account_output_model = account_ns.model('FiatAccountOutput', {
    'user_id': fields.String(required=True),
    'balance': fields.Float(required=True),
    'currency_code': fields.String(required=True),
    'updated': fields.DateTime
})

fiat_account_input_model = account_ns.model('FiatAccountInput', {
    'user_id': fields.String(required=True),
    'balance': fields.Float(required=True),
    'currency_code': fields.String(required=True)
})

fiat_account_update_model = account_ns.model('FiatAccountUpdate', {
    'amount_changed': fields.Float(required=True),
    })

##### CRUD Resource Definitions #####

# --- Fiat Account Endpoints ---

# Currency Routes
@currency_ns.route('/')
class FiatCurrencyList(Resource):
    @currency_ns.marshal_list_with(fiat_currency_output_model)
    def get(self):
        """Get all fiat currencies"""
        return FiatCurrency.query.all()

    @currency_ns.expect(fiat_currency_input_model, validate=True)
    @currency_ns.marshal_with(fiat_currency_output_model, code=201)
    def post(self):
        """Create a new fiat currency"""
        try:
            data = request.json
            new_currency = FiatCurrency(
                currency_code=data.get('currency_code'),
                rate=data.get('rate')
            )
            db.session.add(new_currency)
            db.session.commit()
            return new_currency, 201
        except Exception as e:
            currency_ns.abort(400, f'Failed to create fiat currency: {str(e)}')

@currency_ns.route('/<string:currency_code>')
class FiatCurrencyResource(Resource):
    @currency_ns.marshal_with(fiat_currency_output_model)
    def get(self, currency_code):
        """Get a fiat currency by code"""
        return FiatCurrency.query.get_or_404(currency_code)

    @currency_ns.expect(fiat_currency_update_model, validate=True)
    @currency_ns.marshal_with(fiat_currency_output_model)
    def put(self, currency_code):
        """Update a fiat currency"""
        try:
            currency = FiatCurrency.query.get_or_404(currency_code)
            data = request.json
            currency.rate = data.get('rate')
            db.session.commit()
            return currency
        except Exception as e:
            currency_ns.abort(400, f'Failed to update fiat currency: {str(e)}')
            
    def delete(self, currency_code):
        """Delete a fiat currency"""
        try:
            currency = FiatCurrency.query.get_or_404(currency_code)
            db.session.delete(currency)
            db.session.commit()
            return {'message': 'Fiat currency deleted successfully'}
        except Exception as e:
            currency_ns.abort(400, f'Failed to delete fiat currency: {str(e)}')

# Account Routes
@account_ns.route('/')
class FiatAccountList(Resource):
    @account_ns.marshal_list_with(fiat_account_output_model)
    def get(self):
        """Get all fiat accounts"""
        return FiatAccount.query.all()

    @account_ns.expect(fiat_account_input_model, validate=True)
    @account_ns.marshal_with(fiat_account_output_model, code=201)
    def post(self):
        """Create a new fiat account"""
        try:
            data = request.json
            new_account = FiatAccount(
                user_id=data.get('user_id'),
                balance=data.get('balance'),
                currency_code=data.get('currency_code')
            )
            db.session.add(new_account)
            db.session.commit()
            return new_account, 201
        except Exception as e:
            account_ns.abort(400, f'Failed to create fiat account: {str(e)}')

@account_ns.route('/<string:user_id>/<string:currency_code>')
class FiatAccountResource(Resource):
    @account_ns.marshal_with(fiat_account_output_model)
    def get(self, user_id, currency_code):
        """Get a fiat account by user ID and currency code"""
        return FiatAccount.query.filter_by(user_id=user_id, currency_code=currency_code).first_or_404()

    @account_ns.expect(fiat_account_update_model, validate=True)
    @account_ns.marshal_with(fiat_account_output_model)
    def put(self, user_id, currency_code):
        """Update a fiat account balance"""
        try:
            account = FiatAccount.query.filter_by(user_id=user_id, currency_code=currency_code).first_or_404()
            data = request.json
            amount_changed = data.get('amount_changed', 0)
            
            if account.balance + amount_changed < 0:
                account_ns.abort(400, 'Insufficient balance')
            
            account.balance += amount_changed
            account.updated = func.now()
            db.session.commit()
            return account
        except Exception as e:
            account_ns.abort(400, f'Failed to update fiat account: {str(e)}')

    def delete(self, user_id, currency_code):
        """Delete a fiat account"""
        try:
            account = FiatAccount.query.filter_by(user_id=user_id, currency_code=currency_code).first_or_404()
            db.session.delete(account)
            db.session.commit()
            return {'message': 'Fiat account deleted successfully'}
        except Exception as e:
            account_ns.abort(400, f'Failed to delete fiat account: {str(e)}')

##### Seeding #####
# Provide seed data for all tables
# def seed_data():
#     try:
#         with open("seeddata.json", "r") as file:
#             data = json.load(file)

#         # 1) Insert FiatCurrency data
#         fiat_currencies_data = data.get("fiatCurrencies", [])
#         for currency in fiat_currencies_data:
#             # Skip if currency already exists
#             if FiatCurrency.query.get(currency["currency_code"]):
#                 print(f"Skipping currency '{currency['currency_code']}' as it already exists.")
#                 continue

#             new_currency = FiatCurrency(
#                 currency_code=currency["currency_code"],
#                 rate=currency["rate"]
#             )
#             db.session.add(new_currency)
#         db.session.commit()

#         # 2) Insert FiatAccount data
#         fiat_accounts_data = data.get("fiatAccounts", [])
#         for acct in fiat_accounts_data:
#             # Skip if account already exists (using user_id as primary key)
#             if FiatAccount.query.get(acct["user_id"]):
#                 print(f"Skipping fiat account for user_id '{acct['user_id']}' as it already exists.")
#                 continue

#             new_acct = FiatAccount(
#                 user_id=acct["user_id"],
#                 balance=acct["balance"],
#                 currency_code=acct["currency_code"]
#             )
#             db.session.add(new_acct)
#         db.session.commit()

#         # 3) Insert FiatTransaction data
#         fiat_transactions_data = data.get("fiatTransactions", [])
#         for txn in fiat_transactions_data:
#             # Create a new transaction. transaction_id is auto-generated.
#             new_txn = FiatTransaction(
#                 user_id=txn["user_id"],
#                 amount=txn["amount"],
#                 type=txn["type"],
#                 status=txn["status"]
#             )
#             db.session.add(new_txn)
#         db.session.commit()

#         # 4) Insert FiatCryptoTrade data
#         fiat_crypto_trades_data = data.get("fiatCryptoTrades", [])
#         for trade in fiat_crypto_trades_data:
#             # Create a new crypto trade. transaction_id is auto-generated.
#             new_trade = FiatCryptoTrade(
#                 user_id=trade["user_id"],
#                 wallet_id=trade["wallet_id"],
#                 from_amount=trade["from_amount"],
#                 to_amount=trade["to_amount"],
#                 direction=trade["direction"],
#                 status=trade["status"]
#             )
#             db.session.add(new_trade)
#         db.session.commit()

#         print("Seed data successfully loaded from seeddata.json.")

#     except IntegrityError as e:
#         db.session.rollback()
#         print(f"Data seeding failed due to integrity error: {e}")
#     except FileNotFoundError:
#         print("seeddata.json not found. Skipping seeding.")

# Add name spaces into api
api.add_namespace(currency_ns)
api.add_namespace(account_ns)

if __name__ == '__main__':
    # with app.app_context():
    #     seed_data()
    app.run(host='0.0.0.0', port=5000, debug=True)