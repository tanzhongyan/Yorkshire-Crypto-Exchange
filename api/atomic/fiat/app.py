from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
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
    DB_HOST = "postgres" \
    ""  # Docker network name
    DB_PORT = "5432"
else:
    DB_HOST = "localhost"  # Local environment
    DB_PORT = "5433"

DB_NAME = os.getenv("DB_NAME", "fiat_db")
DB_USER = os.getenv("DB_USER", "fiat_user")
DB_PASS = os.getenv("DB_PASS", "password")

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

blueprint = Blueprint('api', __name__, url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Fiat API', description='Fiat API for Yorkshire Crypto Exchange')
app.register_blueprint(blueprint)

fiat_ns = Namespace('account', description='Fiat account operations')
transaction_ns = Namespace('transaction', description='Fiat transaction operations')
trade_ns = Namespace('trade', description='Fiat trade operations')

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
        UUID(as_uuid=True),
        db.ForeignKey('user_account.user_id', ondelete='SET NULL'),
        primary_key=True
    )
    balance = db.Column(db.Numeric(18, 8), nullable=False, default=0.0)
    currency_code = db.Column(
        db.String(3),
        db.ForeignKey('fiat_currency.currency_code'),
        nullable=False
    )
    last_updated = db.Column(db.DateTime(timezone=True), server_default=func.now())


class FiatTransaction(db.Model):
    __tablename__ = 'fiat_transaction'
    transaction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('user_account.user_id', ondelete='SET NULL'),
        nullable=False
    )
    amount = db.Column(db.Numeric(18, 8), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(15), nullable=False, default='processing')
    creation = db.Column(db.DateTime(timezone=True), server_default=func.now())
    confirmation = db.Column(db.DateTime(timezone=True), nullable=True)


class FiatCryptoTrade(db.Model):
    __tablename__ = 'fiat_crypto_trade'
    transaction_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('user_account.user_id', ondelete='SET NULL'),
        nullable=False
    )
    wallet_id = db.Column(
        UUID(as_uuid=True),
        db.ForeignKey('crypto_wallet.wallet_id', ondelete='SET NULL'),
        nullable=False
    )
    from_amount = db.Column(db.Numeric(18, 8), nullable=False)
    to_amount = db.Column(db.Numeric(18, 8), nullable=False)
    direction = db.Column(db.String(15), nullable=False)
    limit_price = db.Column(db.Numeric(18, 8), nullable=True)
    status = db.Column(db.String(15), nullable=False, default='processing')
    creation = db.Column(db.DateTime(timezone=True), server_default=func.now())
    confirmation = db.Column(db.DateTime(timezone=True), nullable=True)


##### Namespaces #####
fiat_ns = Namespace('account', description='Fiat account operations')
transaction_ns = Namespace('transaction', description='Fiat transaction operations')
trade_ns = Namespace('trade', description='Fiat trade operations')

##### CRUD Resource Definitions #####

# --- Fiat Account Endpoints ---

@fiat_ns.route('')
class FiatAccountListResource(Resource):
    def get(self):
        """Fetch all user accounts"""
        accounts = FiatAccount.query.all()
        result = []
        for acct in accounts:
            result.append({
                'user_id': str(acct.user_id),
                'balance': float(acct.balance),
                'currency_code': acct.currency_code,
                'last_updated': acct.last_updated.isoformat() if acct.last_updated else None
            })
        return jsonify(result)

@fiat_ns.route('/<string:user_id>')
class FiatAccountResource(Resource):
    def get(self, user_id):
        """Fetch one fiat account using userId"""
        acct = FiatAccount.query.get(user_id)
        if not acct:
            return {'message': 'Fiat account not found'}, 404
        result = {
            'user_id': str(acct.user_id),
            'balance': float(acct.balance),
            'currency_code': acct.currency_code,
            'last_updated': acct.last_updated.isoformat() if acct.last_updated else None
        }
        return jsonify(result)

    def post(self, user_id):
        """Create one fiat account using userId"""
        data = request.get_json()
        if FiatAccount.query.get(user_id):
            return {'message': 'Account already exists'}, 400
        new_acct = FiatAccount(
            user_id=user_id,
            balance=data.get('balance', 0.0),
            currency_code=data.get('currency_code')
        )
        db.session.add(new_acct)
        db.session.commit()
        return {'message': 'Account created'}, 201

    def put(self, user_id):
        """Update one fiat account using userId"""
        data = request.get_json()
        acct = FiatAccount.query.get(user_id)
        if not acct:
            return {'message': 'Account not found'}, 404
        acct.balance = data.get('balance', acct.balance)
        acct.currency_code = data.get('currency_code', acct.currency_code)
        db.session.commit()
        return {'message': 'Account updated'}, 200

    def delete(self, user_id):
        """Delete one fiat account using userId"""
        acct = FiatAccount.query.get(user_id)
        if not acct:
            return {'message': 'Account not found'}, 404
        db.session.delete(acct)
        db.session.commit()
        return {'message': 'Account deleted'}, 200

# --- Fiat Transaction Endpoints ---

@transaction_ns.route('')
class FiatTransactionListResource(Resource):
    def get(self):
        """Fetch all fiat transactions of everybody"""
        transactions = FiatTransaction.query.all()
        result = []
        for txn in transactions:
            result.append({
                'transaction_id': txn.transaction_id,
                'user_id': str(txn.user_id),
                'amount': float(txn.amount),
                'type': txn.type,
                'status': txn.status,
                'creation': txn.creation.isoformat() if txn.creation else None,
                'confirmation': txn.confirmation.isoformat() if txn.confirmation else None
            })
        return jsonify(result)

@transaction_ns.route('/user/<string:user_id>')
class FiatTransactionUserResource(Resource):
    def get(self, user_id):
        """Fetch all fiat transactions of a specific user"""
        transactions = FiatTransaction.query.filter_by(user_id=user_id).all()
        result = []
        for txn in transactions:
            result.append({
                'transaction_id': txn.transaction_id,
                'user_id': str(txn.user_id),
                'amount': float(txn.amount),
                'type': txn.type,
                'status': txn.status,
                'creation': txn.creation.isoformat() if txn.creation else None,
                'confirmation': txn.confirmation.isoformat() if txn.confirmation else None
            })
        return jsonify(result)

@transaction_ns.route('/<int:transaction_id>')
class FiatTransactionResource(Resource):
    def get(self, transaction_id):
        """Fetch a specific fiat transaction using transactionId"""
        txn = FiatTransaction.query.get(transaction_id)
        if not txn:
            return {'message': 'Transaction not found'}, 404
        result = {
            'transaction_id': txn.transaction_id,
            'user_id': str(txn.user_id),
            'amount': float(txn.amount),
            'type': txn.type,
            'status': txn.status,
            'creation': txn.creation.isoformat() if txn.creation else None,
            'confirmation': txn.confirmation.isoformat() if txn.confirmation else None
        }
        return jsonify(result)

    def post(self, transaction_id):
        """Create a new fiat transaction using transactionId"""
        data = request.get_json()
        if FiatTransaction.query.get(transaction_id):
            return {'message': 'Transaction already exists'}, 400
        new_txn = FiatTransaction(
            transaction_id=transaction_id,
            user_id=data.get('user_id'),
            amount=data.get('amount'),
            type=data.get('type'),
            status=data.get('status', 'processing')
        )
        db.session.add(new_txn)
        db.session.commit()
        return {'message': 'Transaction created'}, 201

    def put(self, transaction_id):
        """Update a specific fiat transaction using transactionId"""
        data = request.get_json()
        txn = FiatTransaction.query.get(transaction_id)
        if not txn:
            return {'message': 'Transaction not found'}, 404
        txn.user_id = data.get('user_id', txn.user_id)
        txn.amount = data.get('amount', txn.amount)
        txn.type = data.get('type', txn.type)
        txn.status = data.get('status', txn.status)
        db.session.commit()
        return {'message': 'Transaction updated'}, 200

    def delete(self, transaction_id):
        """Delete a specific fiat transaction using transactionId"""
        txn = FiatTransaction.query.get(transaction_id)
        if not txn:
            return {'message': 'Transaction not found'}, 404
        db.session.delete(txn)
        db.session.commit()
        return {'message': 'Transaction deleted'}, 200

# --- Fiat Crypto Trade Endpoints ---

@trade_ns.route('')
class TradeListResource(Resource):
    def get(self):
        """Fetch all trade transactions of everybody"""
        trades = FiatCryptoTrade.query.all()
        result = []
        for trade in trades:
            result.append({
                'transaction_id': trade.transaction_id,
                'user_id': str(trade.user_id),
                'wallet_id': str(trade.wallet_id),
                'from_amount': float(trade.from_amount),
                'to_amount': float(trade.to_amount),
                'direction': trade.direction,
                'limit_price': float(trade.limit_price) if trade.limit_price is not None else None,
                'status': trade.status,
                'creation': trade.creation.isoformat() if trade.creation else None,
                'confirmation': trade.confirmation.isoformat() if trade.confirmation else None
            })
        return jsonify(result)

@trade_ns.route('/user/<string:user_id>')
class TradeUserResource(Resource):
    def get(self, user_id):
        """Fetch all trade transactions of a specific user"""
        trades = FiatCryptoTrade.query.filter_by(user_id=user_id).all()
        result = []
        for trade in trades:
            result.append({
                'transaction_id': trade.transaction_id,
                'user_id': str(trade.user_id),
                'wallet_id': str(trade.wallet_id),
                'from_amount': float(trade.from_amount),
                'to_amount': float(trade.to_amount),
                'direction': trade.direction,
                'limit_price': float(trade.limit_price) if trade.limit_price is not None else None,
                'status': trade.status,
                'creation': trade.creation.isoformat() if trade.creation else None,
                'confirmation': trade.confirmation.isoformat() if trade.confirmation else None
            })
        return jsonify(result)

@trade_ns.route('/<int:transaction_id>')
class TradeResource(Resource):
    def get(self, transaction_id):
        """Fetch a specific trade transaction using transactionId"""
        trade = FiatCryptoTrade.query.get(transaction_id)
        if not trade:
            return {'message': 'Trade not found'}, 404
        result = {
            'transaction_id': trade.transaction_id,
            'user_id': str(trade.user_id),
            'wallet_id': str(trade.wallet_id),
            'from_amount': float(trade.from_amount),
            'to_amount': float(trade.to_amount),
            'direction': trade.direction,
            'limit_price': float(trade.limit_price) if trade.limit_price is not None else None,
            'status': trade.status,
            'creation': trade.creation.isoformat() if trade.creation else None,
            'confirmation': trade.confirmation.isoformat() if trade.confirmation else None
        }
        return jsonify(result)

    def post(self, transaction_id):
        """Create a new trade transaction using transactionId"""
        data = request.get_json()
        if FiatCryptoTrade.query.get(transaction_id):
            return {'message': 'Trade already exists'}, 400
        new_trade = FiatCryptoTrade(
            transaction_id=transaction_id,
            user_id=data.get('user_id'),
            wallet_id=data.get('wallet_id'),
            from_amount=data.get('from_amount'),
            to_amount=data.get('to_amount'),
            direction=data.get('direction'),
            limit_price=data.get('limit_price'),
            status=data.get('status', 'processing')
        )
        db.session.add(new_trade)
        db.session.commit()
        return {'message': 'Trade created'}, 201

    def put(self, transaction_id):
        """Update a specific trade transaction using transactionId"""
        data = request.get_json()
        trade = FiatCryptoTrade.query.get(transaction_id)
        if not trade:
            return {'message': 'Trade not found'}, 404
        trade.user_id = data.get('user_id', trade.user_id)
        trade.wallet_id = data.get('wallet_id', trade.wallet_id)
        trade.from_amount = data.get('from_amount', trade.from_amount)
        trade.to_amount = data.get('to_amount', trade.to_amount)
        trade.direction = data.get('direction', trade.direction)
        trade.limit_price = data.get('limit_price', trade.limit_price)
        trade.status = data.get('status', trade.status)
        db.session.commit()
        return {'message': 'Trade updated'}, 200

    def delete(self, transaction_id):
        """Delete a specific trade transaction using transactionId"""
        trade = FiatCryptoTrade.query.get(transaction_id)
        if not trade:
            return {'message': 'Trade not found'}, 404
        db.session.delete(trade)
        db.session.commit()
        return {'message': 'Trade deleted'}, 200
##### Seeding #####
# Provide seed data for all tables
def seed_data():
    try:
        with open("seeddata.json", "r") as file:
            data = json.load(file)

        # 1) Insert FiatCurrency data
        fiat_currencies_data = data.get("fiatCurrencies", [])
        for currency in fiat_currencies_data:
            # Skip if currency already exists
            if FiatCurrency.query.get(currency["currency_code"]):
                print(f"Skipping currency '{currency['currency_code']}' as it already exists.")
                continue

            new_currency = FiatCurrency(
                currency_code=currency["currency_code"],
                rate=currency["rate"]
            )
            db.session.add(new_currency)
        db.session.commit()

        # 2) Insert FiatAccount data
        fiat_accounts_data = data.get("fiatAccounts", [])
        for acct in fiat_accounts_data:
            # Skip if account already exists (using user_id as primary key)
            if FiatAccount.query.get(acct["user_id"]):
                print(f"Skipping fiat account for user_id '{acct['user_id']}' as it already exists.")
                continue

            new_acct = FiatAccount(
                user_id=acct["user_id"],
                balance=acct["balance"],
                currency_code=acct["currency_code"]
            )
            db.session.add(new_acct)
        db.session.commit()

        # 3) Insert FiatTransaction data
        fiat_transactions_data = data.get("fiatTransactions", [])
        for txn in fiat_transactions_data:
            # Create a new transaction. transaction_id is auto-generated.
            new_txn = FiatTransaction(
                user_id=txn["user_id"],
                amount=txn["amount"],
                type=txn["type"],
                status=txn["status"]
            )
            db.session.add(new_txn)
        db.session.commit()

        # 4) Insert FiatCryptoTrade data
        fiat_crypto_trades_data = data.get("fiatCryptoTrades", [])
        for trade in fiat_crypto_trades_data:
            # Create a new crypto trade. transaction_id is auto-generated.
            new_trade = FiatCryptoTrade(
                user_id=trade["user_id"],
                wallet_id=trade["wallet_id"],
                from_amount=trade["from_amount"],
                to_amount=trade["to_amount"],
                direction=trade["direction"],
                status=trade["status"]
            )
            db.session.add(new_trade)
        db.session.commit()

        print("Seed data successfully loaded from seeddata.json.")

    except IntegrityError as e:
        db.session.rollback()
        print(f"Data seeding failed due to integrity error: {e}")
    except FileNotFoundError:
        print("seeddata.json not found. Skipping seeding.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)