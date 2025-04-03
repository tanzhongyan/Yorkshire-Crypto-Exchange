from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from werkzeug.exceptions import HTTPException
from decimal import Decimal
import json
import uuid
import os

##### Configuration #####
API_VERSION = 'v1'
API_ROOT = f'/api/{API_VERSION}/fiat'

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
    'currencyCode': fields.String(attribute='currency_code',required=True),
    'rate': fields.Float(required=True),
    'updated': fields.DateTime
})

fiat_currency_input_model = currency_ns.model('FiatCurrencyInput', {
    'currencyCode': fields.String(attribute='currency_code',required=True),
    'rate': fields.Float(required=True)
})

fiat_currency_update_model = currency_ns.model('FiatCurrencyUpdate', {
    'rate': fields.Float(required=True)
})

# Account Models
fiat_account_output_model = account_ns.model('FiatAccountOutput', {
    'userId': fields.String(attribute='user_id',required=True),
    'balance': fields.Float(required=True),
    'currencyCode': fields.String(attribute='currency_code',required=True),
    'updated': fields.DateTime
})

fiat_account_input_model = account_ns.model('FiatAccountInput', {
    'userId': fields.String(attribute='user_id',required=True),
    'balance': fields.Float(required=True),
    'currencyCode': fields.String(attribute='currency_code',required=True)
})

fiat_account_update_model = account_ns.model('FiatAccountUpdate', {
    'amountChanged': fields.Float(required=True),
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
                currency_code=data.get('currencyCode'),
                rate=data.get('rate')
            )
            db.session.add(new_currency)
            db.session.commit()
            return new_currency, 201
        except Exception as e:
            currency_ns.abort(400, f'Failed to create fiat currency: {str(e)}')

@currency_ns.route('/<string:currencyCode>')
class FiatCurrencyResource(Resource):
    @currency_ns.marshal_with(fiat_currency_output_model)
    def get(self, currencyCode):
        """Get a fiat currency by code"""
        return FiatCurrency.query.get_or_404(currencyCode)

    @currency_ns.expect(fiat_currency_update_model, validate=True)
    @currency_ns.marshal_with(fiat_currency_output_model)
    def put(self, currencyCode):
        """Update a fiat currency"""
        try:
            currency = FiatCurrency.query.get_or_404(currencyCode)
            data = request.json
            currency.rate = data.get('rate')
            db.session.commit()
            return currency
        except Exception as e:
            currency_ns.abort(400, f'Failed to update fiat currency: {str(e)}')
            
    def delete(self, currencyCode):
        """Delete a fiat currency"""
        try:
            currency = FiatCurrency.query.get_or_404(currencyCode)
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
                user_id=data.get('userId'),
                balance=data.get('balance'),
                currency_code=data.get('currencyCode')
            )
            db.session.add(new_account)
            db.session.commit()
            return new_account, 201
        except Exception as e:
            account_ns.abort(400, f'Failed to create fiat account: {str(e)}')

@account_ns.route('/<string:userId>')
class UserFiatAccounts(Resource):
    @account_ns.marshal_list_with(fiat_account_output_model)
    def get(self, userId):
        """Get all fiat accounts for a specific user"""
        accounts = FiatAccount.query.filter_by(user_id=userId).all()
        if not accounts:
            account_ns.abort(404, f'No accounts found for user ID: {userId}')
        return accounts

    def delete(self, userId):
        """Delete all fiat accounts for a specific user"""
        try:
            accounts = FiatAccount.query.filter_by(user_id=userId).all()
            if not accounts:
                account_ns.abort(404, f'No accounts found for user ID: {userId}')
            
            for account in accounts:
                db.session.delete(account)
            
            db.session.commit()
            return {'message': f'All fiat accounts for user {userId} deleted successfully'}
        except Exception as e:
            account_ns.abort(400, f'Failed to delete fiat accounts: {str(e)}')

@account_ns.route('/<string:userId>/<string:currencyCode>')
class FiatAccountResource(Resource):
    @account_ns.marshal_with(fiat_account_output_model)
    def get(self, userId, currencyCode):
        """Get a fiat account by user ID and currency code"""
        return FiatAccount.query.filter_by(user_id=userId, currency_code=currencyCode).first_or_404()

    @account_ns.expect(fiat_account_update_model, validate=True)
    @account_ns.marshal_with(fiat_account_output_model)
    def put(self, userId, currencyCode):
        """Update a fiat account balance"""
        try:
            account = FiatAccount.query.filter_by(user_id=userId, currency_code=currencyCode).first_or_404()
            data = request.json
            amount_changed = data.get('amountChanged', 0)
            
            # Convert float to Decimal via string to maintain precision
            decimal_amount = Decimal(str(amount_changed))
            
            if account.balance + decimal_amount < 0:
                account_ns.abort(400, 'Insufficient balance')
            
            account.balance += decimal_amount
            account.updated = func.now()
            db.session.commit()
            return account
        except Exception as e:
            account_ns.abort(400, f'Failed to update fiat account: {str(e)}')

    def delete(self, userId, currencyCode):
        """Delete a fiat account"""
        try:
            account = FiatAccount.query.filter_by(user_id=userId, currency_code=currencyCode).first_or_404()
            db.session.delete(account)
            db.session.commit()
            return {'message': 'Fiat account deleted successfully'}
        except Exception as e:
            account_ns.abort(400, f'Failed to delete fiat account: {str(e)}')

##### Seeding #####
# Provide seed data for all tables
def seed_data():
    try:
        with open("seeddata.json", "r") as file:
            data = json.load(file)

        # 1) Insert FiatCurrency data
        fiat_currencies_data = data.get("fiatCurrencies", [])
        for currency in fiat_currencies_data:
            # Convert currency code to lowercase for Stripe compatibility
            currency_code = currency["currencyCode"].lower()
            
            # Skip if currency already exists
            if FiatCurrency.query.get(currency_code):
                print(f"Skipping currency '{currency_code}' as it already exists.")
                continue

            new_currency = FiatCurrency(
                currency_code=currency_code,
                rate=currency["rate"]
            )
            db.session.add(new_currency)
        db.session.commit()

        # 2) Insert FiatAccount data
        fiat_accounts_data = data.get("fiatAccounts", [])
        for acct in fiat_accounts_data:
            # Convert currency code to lowercase for Stripe compatibility
            currency_code = acct["currencyCode"].lower()
            
            # Skip if account already exists (using composite primary key)
            existing_account = FiatAccount.query.filter_by(
                user_id=acct["userId"], 
                currency_code=currency_code
            ).first()
            
            if existing_account:
                print(f"Skipping fiat account for user_id '{acct['userId']}' with currency '{currency_code}' as it already exists.")
                continue

            new_acct = FiatAccount(
                user_id=acct["userId"],
                balance=acct["balance"],
                currency_code=currency_code
            )
            db.session.add(new_acct)
        db.session.commit()

        print("Seed data successfully loaded from seeddata.json.")

    except IntegrityError as e:
        db.session.rollback()
        print(f"Data seeding failed due to integrity error: {e}")
    except FileNotFoundError:
        print("seeddata.json not found. Skipping seeding.")

# Add name spaces into api
api.add_namespace(currency_ns)
api.add_namespace(account_ns)

if __name__ == '__main__':
    with app.app_context():
        seed_data()
    app.run(host='0.0.0.0', port=5000, debug=True)