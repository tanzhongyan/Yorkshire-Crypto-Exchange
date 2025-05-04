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
from decimal import Decimal

##### Configuration #####
# Define API version and root path
API_VERSION = 'v1'
API_ROOT = f'/api/{API_VERSION}/orderbook'

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

DB_NAME = os.getenv("DB_NAME", "orderbook_db")
DB_USER = os.getenv("DB_USER", "user")
DB_PASS = os.getenv("DB_PASS", "password")

app.config["SQLALCHEMY_DATABASE_URI"] = f"postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Flask swagger (flask_restx) api documentation
blueprint = Blueprint('api', __name__, url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='OrderBook API', description='OrderBook API for Yorkshire Crypto Exchange')

# Register Blueprint with Flask app
app.register_blueprint(blueprint)

# Custom error handler for more informative 500 errors
@app.errorhandler(Exception)
def handle_exception(e):
    if isinstance(e, HTTPException):
        return jsonify({'error': e.description}), e.code
    return jsonify({'error': str(e)}), 500

# Define namespaces to group api calls together
order_ns = Namespace('order', description='Order related operations')

##### DB table classes declaration - flask migrate #####
class Order(db.Model):
    __tablename__ = 'orders'
    transaction_id = db.Column(db.String(100), primary_key=True)
    user_id = db.Column(db.String(100), nullable=False)
    order_type = db.Column(db.String(20), nullable=True)  # Making nullable as per Swagger
    from_token_id = db.Column(db.String(50), nullable=False)
    to_token_id = db.Column(db.String(50), nullable=False)
    from_amount = db.Column(db.Numeric(18, 8), nullable=False)
    limit_price = db.Column(db.Numeric(18, 8), nullable=False)
    creation = db.Column(db.DateTime(timezone=True), server_default=func.now())

# Order Model
order_api_model = order_ns.model('OrdersAPI', {
    'transactionId': fields.String(required=True, example="7890abcd-ef12-34gh-5678-ijklmnopqrst"),
    'userId': fields.String(required=True, example="a7c396e2-8370-4975-820e-c5ee8e3875c0"),
    'orderType': fields.String(required=False, example="limit"),
    'fromTokenId': fields.String(required=True, example="usdt"),
    'toTokenId': fields.String(required=True, example="btc"),
    'fromAmount': fields.Float(required=True, example=5000.0),
    'limitPrice': fields.Float(required=True, example=65000.0),
    'creation': fields.DateTime(required=True, example="2025-04-08T10:15:30.937Z")
})

# Response Models
result_model = order_ns.model('result', {
    'success': fields.Boolean(required=True, example=True),
    'errorMessage': fields.String(default="")
})

orders_list_result_model = order_ns.model('OrdersAPIListresultRecord', {
    'result': fields.Nested(result_model),
    'orders': fields.List(fields.Nested(order_api_model))
})

order_update_model = order_ns.model('OrderUpdateAPI', {
    'fromAmount': fields.Float(required=True, example=0.1)
})

# Helper function to convert database model to API model format
def db_to_api_model(order):
    """Convert database model to API model format"""
    if not order:
        return None
    
    return {
        'transactionId': order.transaction_id,
        'userId': order.user_id,
        'orderType': order.order_type,
        'fromTokenId': order.from_token_id,
        'toTokenId': order.to_token_id,
        'fromAmount': float(order.from_amount) if order.from_amount is not None else None,
        'limitPrice': float(order.limit_price) if order.limit_price is not None else None,
        'creation': order.creation.isoformat() + "Z" if order.creation else None
    }

##### Order Routes #####
@order_ns.route('/AddOrder')
class AddOrderResource(Resource):
    @order_ns.expect(order_api_model, validate=True)
    @order_ns.marshal_with(result_model)
    def post(self):
        """Add a new order to the orderbook"""
        try:
            data = request.json
            
            # Check if order with transaction_id already exists
            existing_order = Order.query.get(data.get('transactionId'))
            if existing_order:
                return {'success': False, 'errorMessage': 'Order with this transactionId already exists'}, 400
            
            # Convert creation string to datetime if provided
            creation_time = data.get('creation')
            if isinstance(creation_time, str):
                try:
                    creation_time = datetime.fromisoformat(creation_time.replace('Z', '+00:00'))
                except ValueError:
                    creation_time = datetime.utcnow()
            
            # Create new order
            new_order = Order(
                transaction_id=data.get('transactionId'),
                user_id=data.get('userId'),
                order_type=data.get('orderType', 'limit'),
                from_token_id=data.get('fromTokenId'),
                to_token_id=data.get('toTokenId'),
                from_amount=data.get('fromAmount'),
                limit_price=data.get('limitPrice'),
                creation=creation_time
            )
            
            db.session.add(new_order)
            db.session.commit()
            
            return {'success': True, 'errorMessage': ''}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errorMessage': str(e)}, 400

@order_ns.route('/DeleteAllOrders')
class DeleteAllOrdersResource(Resource):
    @order_ns.marshal_with(result_model)
    def delete(self):
        """Delete all orders from the orderbook"""
        try:
            Order.query.delete()
            db.session.commit()
            return {'success': True, 'errorMessage': ''}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errorMessage': str(e)}, 400

@order_ns.route('/DeleteOrder/<string:transactionId>/')
class DeleteOrderResource(Resource):
    @order_ns.marshal_with(result_model)
    def delete(self, transactionId):
        """Delete a specific order from the orderbook"""
        try:
            order = Order.query.get(transactionId)
            if not order:
                return {'success': False, 'errorMessage': 'Order not found'}, 404
            
            db.session.delete(order)
            db.session.commit()
            
            return {'success': True, 'errorMessage': ''}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errorMessage': str(e)}, 400

@order_ns.route('/GetAllOrders')
class GetAllOrdersResource(Resource):
    def get(self):
        """Get all orders from the orderbook"""
        try:
            orders = Order.query.all()
            
            # Convert each order to API format
            api_orders = [db_to_api_model(order) for order in orders]
            
            # Return data in format expected by the API spec
            response = {
                'result': {'success': True, 'errorMessage': ''},
                'orders': api_orders
            }
            
            return response
        except Exception as e:
            return {
                'result': {'success': False, 'errorMessage': str(e)},
                'orders': []
            }, 400

@order_ns.route('/GetOrdersByToken')
class GetOrdersByTokenResource(Resource):
    @order_ns.doc(params={
        'fromTokenId': {'description': 'From Token ID', 'required': True},
        'toTokenId': {'description': 'To Token ID', 'required': True}
    })
    def get(self):
        """Get orders by token IDs"""
        try:
            from_token_id = request.args.get('fromTokenId')
            to_token_id = request.args.get('toTokenId')
            
            if not from_token_id or not to_token_id:
                return {
                    'result': {'success': False, 'errorMessage': 'Both fromTokenId and toTokenId are required'},
                    'orders': []
                }, 400
            
            orders = Order.query.filter_by(
                from_token_id=from_token_id,
                to_token_id=to_token_id
            ).all()
            
            # Convert each order to API format
            api_orders = [db_to_api_model(order) for order in orders]
            
            # Return data in format expected by the API spec
            response = {
                'result': {'success': True, 'errorMessage': ''},
                'orders': api_orders
            }
            
            return response
        except Exception as e:
            return {
                'result': {'success': False, 'errorMessage': str(e)},
                'orders': []
            }, 400

@order_ns.route('/UpdateOrderQuantity/<string:transactionID>/')
class UpdateOrderQuantityResource(Resource):
    @order_ns.expect(order_update_model, validate=True)
    @order_ns.marshal_with(result_model)
    def patch(self, transactionID):
        """Update order quantity"""
        try:
            data = request.json
            
            order = Order.query.get(transactionID)
            if not order:
                return {'success': False, 'errorMessage': 'Order not found'}, 404
            
            # Update from_amount
            order.from_amount = data.get('fromAmount')
            db.session.commit()
            
            return {'success': True, 'errorMessage': ''}
        except Exception as e:
            db.session.rollback()
            return {'success': False, 'errorMessage': str(e)}, 400


# Add name spaces into api
api.add_namespace(order_ns)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)