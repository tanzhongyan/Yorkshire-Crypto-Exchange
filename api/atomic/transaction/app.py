from flask import Flask, jsonify, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, fields, Namespace
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from werkzeug.exceptions import HTTPException
import pika
import json
import os
import uuid
from datetime import datetime

##### Configuration #####
# Define API version and root path
API_VERSION = 'v1'
API_ROOT = f'/api/{API_VERSION}/transaction'

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

DB_NAME = os.getenv("DB_NAME", "transaction_db")
DB_USER = os.getenv("DB_USER", "user")
DB_PASS = os.getenv("DB_PASS", "password")

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask swagger (flask_restx) api documentation
# Creates API documentation automatically
blueprint = Blueprint('api',__name__,url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Transaction API', description='Transaction API for Yorkshire Crypto Exchange')

# Register Blueprint with Flask app
app.register_blueprint(blueprint)

# Custom error handler for more informative 500 errors
@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({'error': e.description}), e.code
    return jsonify({'error': str(e)}), 500

# Define namespaces to group api calls together
# Namespaces are essentially folders that group all APIs calls related to a table
# You can treat it as table_ns
# Its essential that you use this at your routes
fiat_ns = Namespace('fiat', description='Fiat transaction related operations')
fiat_to_crypto_ns = Namespace('fiattocrypto', description='Fiat to crypto transaction related operations')
crypto_ns = Namespace('crypto', description='Crypto transaction related operations')

##### DB table classes declaration - flask migrate #####
# To use flask migrate, you have to create classes for the table of the entity
# Use these classes to define their data type, uniqueness, nullability, and relationships
# This will auto generate migration code for the database, removing the need for us to manually code SQL to initialise database
# Separate the CRUD functions outside of the classes. Better for separation of concern.
class TransactionFiat(db.Model):
    __tablename__ = 'transaction_fiat'
    transaction_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(18, 8), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False)
    type = db.Column(db.String(10), nullable=False)
    status = db.Column(db.String(15), nullable=False)
    creation = db.Column(db.DateTime(timezone=True), server_default=func.now())
    confirmation = db.Column(db.DateTime(timezone=True), nullable=True, onupdate=func.now())

class TransactionFiatToCrypto(db.Model):
    __tablename__ = 'transaction_fiat_to_crypto'
    transaction_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.String(100), nullable=False)  # No ForeignKey due to separate containers
    from_amount = db.Column(db.Numeric(18, 8), nullable=False)
    to_amount = db.Column(db.Numeric(18, 8), nullable=False)
    direction = db.Column(db.String(15), nullable=False)
    limit_price = db.Column(db.Numeric(18, 8), nullable=True)
    status = db.Column(db.String(15), nullable=False)
    creation = db.Column(db.DateTime(timezone=True), server_default=func.now())
    confirmation = db.Column(db.DateTime(timezone=True), nullable=True, onupdate=func.now())
    token_id = db.Column(db.String(15), nullable=False)
    currency_code = db.Column(db.String(3), nullable=False)  # e.g., SGD, USD

class TransactionCrypto(db.Model):
    __tablename__ = 'transaction_crypto'
    transaction_id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = db.Column(db.String(100), nullable=False)
    status = db.Column(db.String(20), nullable=False)
    from_token_id = db.Column(db.String(15), nullable=False)
    from_amount = db.Column(db.Numeric(18, 8), nullable=False)
    from_amount_actual = db.Column(db.Numeric(18, 8), nullable=True)
    to_token_id = db.Column(db.String(15), nullable=False)
    to_amount = db.Column(db.Numeric(18, 8), nullable=False)
    to_amount_actual = db.Column(db.Numeric(18, 8), nullable=True)
    limit_price = db.Column(db.Numeric(18, 8), nullable=True)
    usdt_fee = db.Column(db.Numeric(18, 8), nullable=False)
    creation = db.Column(db.DateTime(timezone=True), server_default=func.now())
    completion = db.Column(db.DateTime(timezone=True), nullable=True, onupdate=func.now())
    order_type = db.Column(db.String(10), nullable=False)

##### RabbitMQ Connection #####
# def send_to_queue(message):
#     connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
#     channel = connection.channel()
#     channel.queue_declare(queue='transaction_logs')
#     channel.basic_publish(exchange='', routing_key='transaction_logs', body=json.dumps(message))
#     connection.close()

##### API Models - flask restx API autodoc #####
# To use flask restx, you will have to define API models with their input types
# For all API models, add a comment to the top to signify its importance
# E.g. Input/Output One/Many user account

# Fiat Transactions
fiat_output_model = fiat_ns.model('FiatTransactionOutput', {
    'transactionId': fields.String(attribute='transaction_id', readonly=True),
    'userId': fields.String(attribute='user_id',required=True),
    'amount': fields.Float(required=True),
    'currencyCode': fields.String(attribute='currency_code', required=True),
    'type': fields.String(required=True),
    'status': fields.String(required=True),
    'creation': fields.DateTime,
    'confirmation': fields.DateTime
})

fiat_input_model = fiat_ns.model('FiatTransactionInput', {
    'userId': fields.String(attribute='user_id',required=True),
    'amount': fields.Float(required=True),
    'currencyCode': fields.String(attribute='currency_code', required=True),
    'type': fields.String(required=True),
    'status': fields.String(required=True)
})

# Fiat to Crypto Transactions
fiattocrypto_output_model = fiat_to_crypto_ns.model('FiatToCryptoOutput', {
    'transactionId': fields.String(attribute='transaction_id', readonly=True),
    'userId': fields.String(attribute='user_id',required=True),
    'fromAmount': fields.Float(attribute='from_amount', required=True),
    'toAmount': fields.Float(attribute='to_amount', required=True),
    'direction': fields.String(required=True),
    'limitPrice': fields.Float(attribute='limit_price', required=True),
    'status': fields.String(required=True),
    'tokenId': fields.String(attribute='token_id', required=False),
    'currencyCode': fields.String(attribute='currency_code', required=True),
    'creation': fields.DateTime,
    'confirmation': fields.DateTime
})

fiattocrypto_input_model = fiat_to_crypto_ns.model('FiatToCryptoInput', {
    'userId': fields.String(attribute='user_id',required=True),
    'fromAmount': fields.Float(attribute='from_amount', required=True),
    'toAmount': fields.Float(attribute='to_amount', required=True),
    'direction': fields.String(required=True),
    'limitPrice': fields.Float(attribute='limit_price', required=True),
    'status': fields.String(required=True),
    'tokenId': fields.String(attribute='token_id', required=False),
    'currencyCode': fields.String(attribute='currency_code', required=True)
})

# Crypto Transactions
crypto_output_model = crypto_ns.model('CryptoTransactionOutput', {
    'transactionId': fields.String(attribute='transaction_id', readonly=True),
    'userId': fields.String(attribute='user_id',required=True),
    'status': fields.String(required=True),
    'fromTokenId': fields.String(attribute='from_token_id', required=True),
    'fromAmount': fields.Float(attribute='from_amount', required=True),
    'fromAmountActual': fields.Float(attribute='from_amount_actual'),
    'toTokenId': fields.String(attribute='to_token_id', required=True),
    'toAmount': fields.Float(attribute='to_amount', required=True),
    'toAmountActual': fields.Float(attribute='to_amount_actual'),
    'limitPrice': fields.Float(attribute='limit_price', required=True),
    'usdtFee': fields.Float(attribute='usdt_fee', required=True),
    'creation': fields.DateTime,
    'completion': fields.DateTime,
    'orderType': fields.String(attribute='order_type', required=True)
})

crypto_input_model = crypto_ns.model('CryptoTransactionInput', {
    'userId': fields.String(attribute='user_id',required=True),
    'status': fields.String(required=True),
    'fromTokenId': fields.String(attribute='from_token_id', required=True),
    'fromAmount': fields.Float(attribute='from_amount', required=True),
    'fromAmountActual': fields.Float(attribute='from_amount_actual'),
    'toTokenId': fields.String(attribute='to_token_id', required=True),
    'toAmount': fields.Float(attribute='to_amount', required=True),
    'toAmountActual': fields.Float(attribute='to_amount_actual'),
    'limitPrice': fields.Float(attribute='limit_price', required=True),
    'usdtFee': fields.Float(attribute='usdt_fee', required=True),
    'orderType': fields.String(attribute='order_type', required=True)
})

#### API actions - flask restx API autodoc #####
# To use flask restx, you will also have to separate the CRUD actions from the DB table classes

##### Fiat Transaction Routes #####
@fiat_ns.route('/')
class FiatTransactionList(Resource):
    @fiat_ns.marshal_list_with(fiat_output_model)
    def get(self):
        """Get all fiat transactions"""
        return TransactionFiat.query.all()

    @fiat_ns.expect(fiat_input_model, validate=True)
    @fiat_ns.marshal_with(fiat_output_model, code=201)
    def post(self):
        """Create a new fiat transaction"""
        data = request.json
        new_transaction = TransactionFiat(
            user_id=data.get('userId'),
            amount=data.get('amount'),
            currency_code=data.get('currencyCode'),
            type=data.get('type'),
            status=data.get('status')
        )
        try:
            db.session.add(new_transaction)
            db.session.commit()
            # send_to_queue({'transaction_id': str(new_transaction.transaction_id), 'type': 'fiat', 'action': 'created'})
            return new_transaction, 201
        except Exception as e:
            fiat_ns.abort(400, f'Failed to create fiat transaction: {str(e)}')

@fiat_ns.route('/<string:transactionId>')
class FiatTransactionResource(Resource):
    @fiat_ns.marshal_with(fiat_output_model)
    def get(self, transactionId):
        """Get a fiat transaction by ID"""
        return TransactionFiat.query.get_or_404(transactionId)

    @fiat_ns.expect(fiat_input_model)
    @fiat_ns.marshal_with(fiat_output_model)
    def put(self, transactionId):
        """Update a fiat transaction"""
        transaction = TransactionFiat.query.get_or_404(transactionId)
        data = request.json
        transaction.user_id = data.get('userId', transaction.user_id)
        transaction.amount = data.get('amount', transaction.amount)
        transaction.type = data.get('type', transaction.type)
        transaction.status = data.get('status', transaction.status)
        transaction.currency_code = data.get('currencyCode', transaction.currency_code)
        try:
            db.session.commit()
            return transaction
        except Exception as e:
            fiat_ns.abort(400, f'Failed to update fiat transaction: {str(e)}')

    def delete(self, transactionId):
        """Delete a fiat transaction"""
        transaction = TransactionFiat.query.get_or_404(transactionId)
        try:
            db.session.delete(transaction)
            db.session.commit()
            return {'message': 'Transaction deleted successfully'}
        except Exception as e:
            fiat_ns.abort(400, f'Failed to delete fiat transaction: {str(e)}')

@fiat_ns.route('user/<string:userId>')
class FiatTransactionsByUser(Resource):
    @fiat_ns.marshal_list_with(fiat_output_model)
    def get(self, userId):
        """Get all fiat transactions for a specific user"""
        return TransactionFiat.query.filter_by(user_id=userId).all()

##### FiatToCrypto Transaction Routes #####
@fiat_to_crypto_ns.route('/')
class FiatToCryptoTransactionList(Resource):
    @fiat_to_crypto_ns.marshal_list_with(fiattocrypto_output_model)
    def get(self):
        """Get all fiat-to-crypto transactions"""
        return TransactionFiatToCrypto.query.all()

    @fiat_to_crypto_ns.expect(fiattocrypto_input_model, validate=True)
    @fiat_to_crypto_ns.marshal_with(fiattocrypto_output_model, code=201)
    def post(self):
        """Create a new fiat-to-crypto transaction"""
        data = request.json
        new_transaction = TransactionFiatToCrypto(
            user_id=data.get('userId'),
            from_amount=data.get('fromAmount'),
            to_amount=data.get('toAmount'),
            direction=data.get('direction'),
            limit_price=data.get('limitPrice'),
            status=data.get('status'),
            token_id=data.get('tokenId'),  # Default to USDT
            currency_code=data.get('currencyCode')
        )
        try:
            db.session.add(new_transaction)
            db.session.commit()
            # send_to_queue({'transaction_id': str(new_transaction.transaction_id), 'type': 'fiattocrypto', 'action': 'created'})
            return new_transaction, 201
        except Exception as e:
            fiat_to_crypto_ns.abort(400, f'Failed to create fiat-to-crypto transaction: {str(e)}')

@fiat_to_crypto_ns.route('/<string:transactionId>')
class FiatToCryptoTransactionResource(Resource):
    @fiat_to_crypto_ns.marshal_with(fiattocrypto_output_model)
    def get(self, transactionId):
        """Get a fiat-to-crypto transaction by ID"""
        return TransactionFiatToCrypto.query.get_or_404(transactionId)

    @fiat_to_crypto_ns.expect(fiattocrypto_input_model, validate=True)
    @fiat_to_crypto_ns.marshal_with(fiattocrypto_output_model)
    def put(self, transactionId):
        """Update a fiat-to-crypto transaction"""
        transaction = TransactionFiatToCrypto.query.get_or_404(transactionId)
        data = request.json
        try:
            # Map from camelCase (API) to snake_case (database)
            camel_to_snake = {
                'userId': 'user_id',
                'fromAmount': 'from_amount',
                'toAmount': 'to_amount',
                'direction': 'direction',
                'limitPrice': 'limit_price',
                'status': 'status',
                'tokenId': 'token_id',         # New field mapping
                'currencyCode': 'currency_code' # New field mapping
            }
            
            for camel_key, snake_attr in camel_to_snake.items():
                if camel_key in data:
                    setattr(transaction, snake_attr, data.get(camel_key))
            
            db.session.commit()
            return transaction
        except Exception as e:
            fiat_to_crypto_ns.abort(400, f'Failed to update fiat-to-crypto transaction: {str(e)}')

    def delete(self, transactionId):
        """Delete a fiat-to-crypto transaction"""
        transaction = TransactionFiatToCrypto.query.get_or_404(transactionId)
        try:
            db.session.delete(transaction)
            db.session.commit()
            return {'message': 'Transaction deleted successfully'}
        except Exception as e:
            fiat_to_crypto_ns.abort(400, f'Failed to delete fiat-to-crypto transaction: {str(e)}')

@fiat_to_crypto_ns.route('/user/<string:userId>')
class FiatToCryptoTransactionsByUser(Resource):
    @fiat_to_crypto_ns.marshal_list_with(fiattocrypto_output_model)
    def get(self, userId):
        """Get all fiat-to-crypto transactions for a specific user"""
        return TransactionFiatToCrypto.query.filter_by(user_id=userId).all()

##### Crypto Transaction Routes #####
@crypto_ns.route('/')
class CryptoTransactionList(Resource):
    @crypto_ns.marshal_list_with(crypto_output_model)
    def get(self):
        """Get all crypto transactions"""
        return TransactionCrypto.query.all()

    @crypto_ns.expect(crypto_input_model, validate=True)
    @crypto_ns.marshal_with(crypto_output_model, code=201)
    def post(self):
        """Create a new crypto transaction"""
        data = request.json
        new_transaction = TransactionCrypto(
            user_id=data.get('userId'),
            status=data.get('status'),
            from_token_id=data.get('fromTokenId'),
            from_amount=data.get('fromAmount'),
            from_amount_actual=data.get('fromAmountActual'),
            to_token_id=data.get('toTokenId'),
            to_amount=data.get('toAmount'),
            to_amount_actual=data.get('toAmountActual'),
            limit_price=data.get('limitPrice'),
            usdt_fee=data.get('usdtFee'),
            order_type=data.get('orderType')
        )
        try:
            db.session.add(new_transaction)
            db.session.commit()
            # send_to_queue({'transaction_id': str(new_transaction.transaction_id), 'type': 'crypto', 'action': 'created'})
            return new_transaction, 201
        except Exception as e:
            crypto_ns.abort(400, f'Failed to create crypto transaction: {str(e)}')

@crypto_ns.route('/<string:transactionId>')
class CryptoTransactionResource(Resource):
    @crypto_ns.marshal_with(crypto_output_model)
    def get(self, transactionId):
        """Get a crypto transaction by transaction ID"""
        return TransactionCrypto.query.get_or_404(transactionId)

    @crypto_ns.expect(crypto_input_model, validate=True)
    @crypto_ns.marshal_with(crypto_output_model)
    def put(self, transactionId):
        """Update a crypto transaction"""
        transaction = TransactionCrypto.query.get_or_404(transactionId)
        data = request.json
        try:
            # Map from camelCase (API) to snake_case (database)
            camel_to_snake = {
                'userId': 'user_id',
                'status': 'status',
                'fromTokenId': 'from_token_id',
                'fromAmount': 'from_amount',
                'fromAmountActual': 'from_amount_actual',
                'toTokenId': 'to_token_id',
                'toAmount': 'to_amount',
                'toAmountActual': 'to_amount_actual',
                'limitPrice': 'limit_price',
                'usdtFee': 'usdt_fee',
                'orderType': 'order_type'
            }
            
            for camel_key, snake_attr in camel_to_snake.items():
                if camel_key in data:
                    setattr(transaction, snake_attr, data.get(camel_key))
            
            db.session.commit()
            return transaction
        except Exception as e:
            crypto_ns.abort(400, f'Failed to update crypto transaction: {str(e)}')

    def delete(self, transactionId):
        """Delete a crypto transaction"""
        transaction = TransactionCrypto.query.get_or_404(transactionId)
        try:
            db.session.delete(transaction)
            db.session.commit()
            return {'message': 'Transaction deleted successfully'}
        except Exception as e:
            crypto_ns.abort(400, f'Failed to delete crypto transaction: {str(e)}')

@crypto_ns.route('/user/<string:userId>')
class CryptoTransactionsByUser(Resource):
    @crypto_ns.marshal_list_with(crypto_output_model)
    def get(self, userId):
        """Get all crypto transactions for a specific user"""
        return TransactionCrypto.query.filter_by(user_id=userId).all()

##### Seed data ##### 
# def seed_data():
#     with open('seeddata.json') as f:
#         data = json.load(f)
#         for entry in data:
#             transaction = TransactionLog(**entry)
#             db.session.add(transaction)
#         db.session.commit()
#         print("Seed data inserted successfully.")

# Add name spaces into api
api.add_namespace(fiat_ns)
api.add_namespace(fiat_to_crypto_ns)
api.add_namespace(crypto_ns)

if __name__ == '__main__':
    # with app.app_context():
    #     seed_data()
    app.run(host='0.0.0.0', port=5000, debug=True)