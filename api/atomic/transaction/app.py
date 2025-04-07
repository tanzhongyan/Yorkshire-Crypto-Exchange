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
transaction_log_ns = Namespace('aggregated', description='Aggregated transaction logs operations')

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
    'orderType': fields.String(attribute='order_type', required=True)
})

# Aggregated Transaction Logs
transaction_log_output_model = transaction_log_ns.model('TransactionLogOutput', {
    'transactionId': fields.String(attribute='transaction_id'),
    'userId': fields.String(attribute='user_id'),
    'status': fields.String(),
    'creationDate': fields.DateTime(attribute='creation_date'),
    'transactionType': fields.String(attribute='transaction_type'),
    # Common financial fields
    'amount': fields.Float(attribute='amount', required=False),
    'currencyCode': fields.String(attribute='currency_code', required=False),
    # Fiat specific fields
    'type': fields.String(required=False),
    'confirmation': fields.DateTime(required=False),
    # Fiat to Crypto specific fields
    'fromAmount': fields.Float(attribute='from_amount', required=False),
    'toAmount': fields.Float(attribute='to_amount', required=False),
    'direction': fields.String(required=False),
    'limitPrice': fields.Float(attribute='limit_price', required=False),
    'tokenId': fields.String(attribute='token_id', required=False),
    # Crypto specific fields
    'fromTokenId': fields.String(attribute='from_token_id', required=False),
    'fromAmountActual': fields.Float(attribute='from_amount_actual', required=False),
    'toTokenId': fields.String(attribute='to_token_id', required=False),
    'toAmountActual': fields.Float(attribute='to_amount_actual', required=False),
    'orderType': fields.String(attribute='order_type', required=False),
    'completion': fields.DateTime(required=False)
})

# Pagination model for metadata
pagination_model = transaction_log_ns.model('PaginationInfo', {
    'total': fields.Integer(description='Total number of records'),
    'pages': fields.Integer(description='Total number of pages'),
    'page': fields.Integer(description='Current page number'),
    'per_page': fields.Integer(description='Number of records per page')
})

# Combined response model with both data and pagination info
transaction_log_response_model = transaction_log_ns.model('TransactionLogResponse', {
    'transactions': fields.List(fields.Nested(transaction_log_output_model)),
    'pagination': fields.Nested(pagination_model)
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

@transaction_log_ns.route('/')
class TransactionLogList(Resource):
    @transaction_log_ns.doc(params={
        'page': 'Page number (default: 1)',
        'per_page': 'Items per page (default: 10, max: 100)',
        'user_id': 'Filter by user ID (optional)'
    })
    @transaction_log_ns.marshal_with(transaction_log_response_model)
    def get(self):
        """Get all transactions across different types with pagination"""
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Limit max per_page to 100
        user_id = request.args.get('user_id', None)
        
        # Implement the logic to fetch, merge and paginate
        return self.get_paginated_transactions(page, per_page, user_id)
    
    def get_paginated_transactions(self, page, per_page, user_id=None):
        """Helper method to fetch and paginate transactions from all three tables"""
        # We'll query each table separately, then combine and sort
        # First, count total records to know what to fetch
        
        # Count fiat transactions
        fiat_query = TransactionFiat.query
        if user_id:
            fiat_query = fiat_query.filter_by(user_id=user_id)
        fiat_count = fiat_query.count()
        
        # Count fiat to crypto transactions
        fiat_to_crypto_query = TransactionFiatToCrypto.query
        if user_id:
            fiat_to_crypto_query = fiat_to_crypto_query.filter_by(user_id=user_id)
        fiat_to_crypto_count = fiat_to_crypto_query.count()
        
        # Count crypto transactions
        crypto_query = TransactionCrypto.query
        if user_id:
            crypto_query = crypto_query.filter_by(user_id=user_id)
        crypto_count = crypto_query.count()
        
        # Calculate total records and total pages
        total_records = fiat_count + fiat_to_crypto_count + crypto_count
        total_pages = (total_records + per_page - 1) // per_page if total_records > 0 else 1
        
        # To be efficient, we'll fetch a bit more than we need from each table
        # This approach won't be perfect for all distributions of data but will work well in most cases
        # The multiplier determines how many records to fetch from each table relative to per_page
        fetch_multiplier = 3  # Fetch 3x per_page from each table to handle imbalanced distributions
        fetch_limit = per_page * fetch_multiplier
        
        # Fetch transactions from each table with order by date desc
        fiat_txns = fiat_query.order_by(TransactionFiat.creation.desc()).limit(fetch_limit).all()
        fiat_to_crypto_txns = fiat_to_crypto_query.order_by(TransactionFiatToCrypto.creation.desc()).limit(fetch_limit).all()
        crypto_txns = crypto_query.order_by(TransactionCrypto.creation.desc()).limit(fetch_limit).all()
        
        # Transform data into a standardized format
        all_transactions = []
        
        # Process fiat transactions
        for txn in fiat_txns:
            all_transactions.append({
                'transaction_id': str(txn.transaction_id),
                'user_id': txn.user_id,
                'status': txn.status,
                'creation_date': txn.creation,
                'transaction_type': 'fiat',
                'amount': float(txn.amount),
                'currency_code': txn.currency_code,
                'type': txn.type,
                'confirmation': txn.confirmation
            })
        
        # Process fiat to crypto transactions
        for txn in fiat_to_crypto_txns:
            all_transactions.append({
                'transaction_id': str(txn.transaction_id),
                'user_id': txn.user_id,
                'status': txn.status,
                'creation_date': txn.creation,
                'transaction_type': 'fiat_to_crypto',
                'from_amount': float(txn.from_amount),
                'to_amount': float(txn.to_amount),
                'direction': txn.direction,
                'limit_price': float(txn.limit_price) if txn.limit_price else None,
                'token_id': txn.token_id,
                'currency_code': txn.currency_code,
                'confirmation': txn.confirmation
            })
        
        # Process crypto transactions
        for txn in crypto_txns:
            # For crypto, we use the 'completion' date if available, otherwise 'creation'
            date_for_sorting = txn.completion if txn.completion else txn.creation
            all_transactions.append({
                'transaction_id': str(txn.transaction_id),
                'user_id': txn.user_id,
                'status': txn.status,
                'creation_date': txn.creation,
                'sort_date': date_for_sorting,  # Additional field just for sorting
                'transaction_type': 'crypto',
                'from_token_id': txn.from_token_id,
                'from_amount': float(txn.from_amount),
                'from_amount_actual': float(txn.from_amount_actual) if txn.from_amount_actual else None,
                'to_token_id': txn.to_token_id,
                'to_amount': float(txn.to_amount),
                'to_amount_actual': float(txn.to_amount_actual) if txn.to_amount_actual else None,
                'limit_price': float(txn.limit_price) if txn.limit_price else None,
                'completion': txn.completion,
                'order_type': txn.order_type
            })
        
        # Sort all transactions by date in descending order
        # For crypto transactions, use the sort_date field we added
        all_transactions.sort(key=lambda x: x.get('sort_date', x['creation_date']), reverse=True)
        
        # Apply pagination
        start = (page - 1) * per_page
        end = start + per_page
        paginated_transactions = all_transactions[start:end]
        
        # Clean up any temporary fields we added for sorting
        for txn in paginated_transactions:
            if 'sort_date' in txn:
                del txn['sort_date']
        
        # Return the paginated results with pagination metadata
        return {
            'transactions': paginated_transactions,
            'pagination': {
                'total': total_records,
                'pages': total_pages,
                'page': page,
                'per_page': per_page
            }
        }

@transaction_log_ns.route('/user/<string:userId>')
class TransactionLogByUser(Resource):
    @transaction_log_ns.doc(params={
        'page': 'Page number (default: 1)',
        'per_page': 'Items per page (default: 10, max: 100)'
    })
    @transaction_log_ns.marshal_with(transaction_log_response_model)
    def get(self, userId):
        """Get all transactions for a specific user with pagination"""
        # Get query parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)  # Limit max per_page to 100
        
        # Reuse the same logic but filter by user_id
        txn_list = TransactionLogList()
        return txn_list.get_paginated_transactions(page, per_page, user_id=userId)

##### Seed data ##### 
def seed_data():
    try:
        # Check if the seeddata.json exists, if not, create it with our data
        try:
            with open("seeddata.json", "r") as file:
                data = json.load(file)
                print("Loading existing seeddata.json file.")
        except FileNotFoundError:
            print("seeddata.json not found. Creating default seed data.")
            data = {
                "transactionFiat": [
                    {
                        "userId": "a7c396e2-8370-4975-820e-c5ee8e3875c0",
                        "amount": 1000.0,
                        "currencyCode": "sgd",
                        "type": "deposit",
                        "status": "pending"
                    },
                    {
                        "userId": "a7c396e2-8370-4975-820e-c5ee8e3875c0",
                        "amount": 2000.0,
                        "currencyCode": "usd",
                        "type": "deposit",
                        "status": "pending"
                    }
                ],
                "transactionFiatToCrypto": [
                    {
                        "userId": "a7c396e2-8370-4975-820e-c5ee8e3875c0",
                        "fromAmount": 1000.0,
                        "toAmount": 1000.0,
                        "direction": "fiattocrypto",
                        "limitPrice": 1.0,
                        "status": "pending",
                        "tokenId": "usdt",
                        "currencyCode": "usd"
                    }
                ]
            }
            
            # Save the seed data to a file
            with open("seeddata.json", "w") as file:
                json.dump(data, file, indent=2)
                print("Created seeddata.json with initial data.")

        # Insert fiat transaction data
        fiat_transactions = data.get("transactionFiat", [])
        
        # Check for existing fiat transactions to avoid duplicates
        for tx in fiat_transactions:
            # Check if transaction already exists with similar attributes
            existing_transaction = TransactionFiat.query.filter_by(
                user_id=tx["userId"],
                amount=tx["amount"],
                currency_code=tx["currencyCode"].lower(),
                type=tx["type"]
            ).first()
            
            if existing_transaction:
                print(f"Skipping duplicate fiat transaction for user: {tx['userId']}, amount: {tx['amount']} {tx['currencyCode']}")
                continue
                
            # Create and add the initial pending transaction
            new_transaction = TransactionFiat(
                user_id=tx["userId"],
                amount=tx["amount"],
                currency_code=tx["currencyCode"].lower(),
                type=tx["type"],
                status="pending"
            )
            db.session.add(new_transaction)
            db.session.flush()  # Flush to get the transaction ID
            
            # Update to completed to trigger confirmation timestamp
            new_transaction.status = "completed"
        
        # Insert fiat to crypto transaction data
        fiat_to_crypto_transactions = data.get("transactionFiatToCrypto", [])
        
        # Check for existing fiat-to-crypto transactions to avoid duplicates
        for tx in fiat_to_crypto_transactions:
            # Check if transaction already exists with similar attributes
            existing_transaction = TransactionFiatToCrypto.query.filter_by(
                user_id=tx["userId"],
                from_amount=tx["fromAmount"],
                to_amount=tx["toAmount"],
                direction=tx["direction"],
                token_id=tx["tokenId"].lower(),
                currency_code=tx["currencyCode"].lower()
            ).first()
            
            if existing_transaction:
                print(f"Skipping duplicate fiat-to-crypto transaction for user: {tx['userId']}, converting {tx['fromAmount']} {tx['currencyCode']} to {tx['toAmount']} {tx['tokenId']}")
                continue
                
            # Create and add the initial pending transaction
            new_transaction = TransactionFiatToCrypto(
                user_id=tx["userId"],
                from_amount=tx["fromAmount"],
                to_amount=tx["toAmount"],
                direction=tx["direction"],
                limit_price=tx["limitPrice"],
                status="pending",
                token_id=tx["tokenId"].lower(),
                currency_code=tx["currencyCode"].lower()
            )
            db.session.add(new_transaction)
            db.session.flush()  # Flush to get the transaction ID
            
            # Update to completed to trigger confirmation timestamp
            new_transaction.status = "completed"
        
        db.session.commit()
        print("Seed data successfully loaded from seeddata.json.")

    except IntegrityError as e:
        db.session.rollback()
        print(f"Data seeding failed due to integrity error: {e}")
    except Exception as e:
        db.session.rollback()
        print(f"Data seeding failed with error: {e}")

# Add name spaces into api
api.add_namespace(fiat_ns)
api.add_namespace(fiat_to_crypto_ns)
api.add_namespace(crypto_ns)
api.add_namespace(transaction_log_ns)

if __name__ == '__main__':
    with app.app_context():
        seed_data()
    app.run(host='0.0.0.0', port=5000, debug=True)