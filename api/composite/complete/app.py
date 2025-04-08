from flask import Flask, request, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, Namespace, fields
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import threading
import json
import os
import requests
import smtplib
from dotenv import load_dotenv
import amqp_lib
import logging

# Load environment variables
load_dotenv()

# Configure logging at the application startup
logging.basicConfig(
    level=logging.DEBUG,  # Set to DEBUG during testing
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Config
API_VERSION = 'v1'
API_ROOT = f'/api/{API_VERSION}'

app = Flask(__name__)
CORS(app)

blueprint = Blueprint('api', __name__, url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Notification Management Service API',
          description='Consumes message from queue and executes transaction update and notifications. APIs provided for testing.', )
app.register_blueprint(blueprint)

notification_ns = Namespace('notification', description='Notification endpoints')
transaction_ns = Namespace('transaction', description='Transaction log endpoints')

# AMQP Configuration
AMQP_HOST = os.getenv("AMQP_HOST", "rabbitmq")
AMQP_PORT = int(os.getenv("AMQP_PORT", "5672"))
EXCHANGE_NAME = "order_topic"
EXCHANGE_TYPE = "topic"
QUEUE_NAME = "notification_service.orders_executed"
ROUTING_KEY = "order.executed"

# Global variables for AMQP connection
connection = None
channel = None

# API URLs
SMU_SMS_URL = "https://smuedu-dev.outsystemsenterprise.com/SMULab_Notification/rest/Notification/SendSMS"
USER_API_URL = os.getenv("USER_API_URL", "http://user-service:5000/api/v1/user")
TRANSACTION_API_URL = os.getenv("TRANSACTION_API_URL", "http://transaction-service:5000/api/v1/transaction")

# Email configuration
GMAIL_USER = os.getenv("GMAIL_USER")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")
EMAIL_SENDER_NAME = "Yorkshire Crypto Exchange"

# Define API models
notification_model = notification_ns.model("NotificationPayload", {
    "userId": fields.String(required=True, description="User ID",
                example="a7c396e2-8370-4975-820e-c5ee8e3875c0"),
    "transactionId": fields.String(required=True, description="Transaction ID",
                example="f47ac10b-58cc-4372-a567-0e02b2c3d479")
})

transaction_update_model = transaction_ns.model('TransactionUpdate', {
    'userId': fields.String(required=True, description='User ID',
                example="a7c396e2-8370-4975-820e-c5ee8e3875c0"),
    'status': fields.String(required=True, description='Transaction status',
                example="completed"),
    'fromAmountActual': fields.Float(required=True, description='Actual from amount',
                example=1000.0),
    'toAmountActual': fields.Float(required=True, description='Actual to amount',
                example=0.02345),
    'details': fields.String(required=False, description='Additional details',
                example="Transaction processed successfully at market rate")
})

sms_model = notification_ns.model('SMSRequest', {
    'mobile': fields.String(required=True, description='Mobile number',
                example="+6512345678"),
    'message': fields.String(required=True, description='SMS message content',
                example="Your crypto purchase of 0.02345 BTC for 1000.00 USD has been completed. Transaction ID: f47ac10b.")
})

email_model = notification_ns.model('EmailRequest', {
    'to': fields.String(required=True, description='Recipient email',
                example="test@test.com"),
    'subject': fields.String(required=True, description='Email subject',
                example="Crypto Transaction Confirmation - Order #f47ac10b"),
    'body': fields.String(required=True, description='Email content',
                example="Dear Test User,\n\nYour crypto purchase has been completed successfully:\n\nAmount: 0.02345 BTC\nCost: 1000.00 USD\nStatus: Completed\nTransaction ID: f47ac10b-58cc-4372-a567-0e02b2c3d479\n\nThank you for using our service.\n\nRegards,\nCrypto Exchange Team")
})

# Connect to AMQP broker
def connect_amqp():
    """Connect to the AMQP broker"""
    global connection
    global channel

    try:
        connection, channel = amqp_lib.connect(
            hostname=AMQP_HOST,
            port=AMQP_PORT,
            exchange_name=EXCHANGE_NAME,
            exchange_type=EXCHANGE_TYPE
        )
        logger.info("Connected to AMQP broker")
        return True
    except Exception as e:
        logger.error(f"Failed to connect to AMQP broker: {e}")
        return False

# Functions for email and SMS
def send_email(to_email, subject, body):
    """Send an email using Gmail SMTP"""
    sender_email = os.getenv("GMAIL_USER")
    sender_password = os.getenv("GMAIL_PASSWORD")
    
    if not sender_email or not sender_password:
        logger.warning("Gmail credentials not provided in environment variables.")
        return False
    
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{EMAIL_SENDER_NAME} <{sender_email}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())
        logger.info(f"Email sent to {to_email}")
        return True
    except Exception as e:
        logger.error(f"Failed to send email: {e}")
        return False

def send_sms(phone_number, message):
    """Send SMS using SMU wrapper"""
    try:
        payload = {
            "mobile": phone_number,
            "message": message
        }
        response = requests.post(SMU_SMS_URL, json=payload)
        response.raise_for_status()
        logger.info(f"SMS sent to {phone_number}")
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send SMS: {e}")
        return None

def get_user_info(user_id):
    """Get user information (email and phone) by user ID"""
    try:
        response = requests.get(f"{USER_API_URL}/account/{user_id}")
        response.raise_for_status()
        user_data = response.json()
        logger.debug(f"Retrieved user info for {user_id}: {user_data}")
        return {
            "email": user_data.get("email"),
            "phone": user_data.get("phone")
        }
    except Exception as e:
        logger.error(f"Failed to get user info: {e}")
        return None

def get_transaction(transaction_id):
    """Get transaction details by ID"""
    try:
        response = requests.get(f"{TRANSACTION_API_URL}/crypto/{transaction_id}")
        response.raise_for_status()
        transaction_data = response.json()
        logger.debug(f"Retrieved transaction {transaction_id}: {transaction_data}")
        return transaction_data
    except Exception as e:
        logger.error(f"Failed to get transaction: {e}")
        return None

def update_transaction(transaction_id, update_data):
    """Update crypto transaction log"""
    try:
        logger.info(f"Updating transaction {transaction_id} with {update_data}")
        response = requests.put(f"{TRANSACTION_API_URL}/crypto/{transaction_id}", json=update_data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to update transaction: {e}")
        return None

def process_message(message_data):
    """Process an order execution message"""
    transaction_id = message_data.get('transactionId')
    user_id = message_data.get('userId')
    status = message_data.get('status')
    from_amount_actual = message_data.get('fromAmountActual')
    to_amount_actual = message_data.get('toAmountActual')
    details = message_data.get('details', '')
    
    logger.info(f"Processing message for transaction {transaction_id}")
    
    # Get the current transaction data
    current_tx = get_transaction(transaction_id)
    
    if current_tx:
        # Create the update data, preserving existing fields
        update_data = {
            'userId': user_id,
            'status': status,
            'fromTokenId': current_tx.get('fromTokenId'),
            'fromAmount': current_tx.get('fromAmount'),
            'fromAmountActual': from_amount_actual,
            'toTokenId': current_tx.get('toTokenId'),
            'toAmount': current_tx.get('toAmount'),
            'toAmountActual': to_amount_actual,
            'limitPrice': current_tx.get('limitPrice'),
            'orderType': current_tx.get('orderType')
        }
        
        update_result = update_transaction(transaction_id, update_data)
        
        if update_result:
            # Get user information
            user_info = get_user_info(user_id)
            
            if user_info:
                # Send notifications
                email = user_info.get('email')
                phone = user_info.get('phone')
                
                # Format notification messages
                email_subject = f"Transaction Update - {transaction_id}"
                email_body = f"""
Dear Customer,

Your transaction {transaction_id} has been {status}.

From amount: {from_amount_actual}
To amount: {to_amount_actual}

{details}

Thank you for using Yorkshire Crypto Exchange.
                """
                
                sms_message = f"Yorkshire Crypto: Your transaction {transaction_id} has been {status}. Login to your account for details."
                
                # Send email
                if email:
                    email_sent = send_email(email, email_subject, email_body.strip())
                    logger.info(f"Email notification {'sent' if email_sent else 'failed'} for transaction {transaction_id}")
                
                # Send SMS
                if phone:
                    sms_result = send_sms(phone, sms_message)
                    logger.info(f"SMS notification sent for transaction {transaction_id}")
    else:
        logger.error(f"Could not find transaction {transaction_id} for update")

def amqp_callback(ch, method, properties, body):
    """AMQP callback function"""
    try:
        message_data = json.loads(body)
        logger.debug(f"Received AMQP message: {message_data}")
        process_message(message_data)
    except Exception as e:
        logger.error(f"Error processing AMQP message: {e}")

def start_consumer():
    """Start consuming messages from RabbitMQ"""
    logger.info("Starting AMQP consumer")
    amqp_lib.start_consuming(
        hostname=AMQP_HOST,
        port=AMQP_PORT,
        exchange_name=EXCHANGE_NAME,
        exchange_type=EXCHANGE_TYPE,
        queue_name=QUEUE_NAME,
        callback=amqp_callback,
        routing_key=ROUTING_KEY
    )

# API routes
@notification_ns.route('/test-notify')
class TestNotify(Resource):
    @notification_ns.expect(notification_model)
    @notification_ns.doc(description="Test endpoint to manually trigger notification")
    def post(self):
        """Test endpoint to manually trigger notification"""
        data = request.json
        transaction_id = data.get('transactionId')
        user_id = data.get('userId')
        
        # Create mock AMQP message
        mock_message = {
            'transactionId': transaction_id,
            'userId': user_id,
            'status': 'COMPLETED',
            'fromAmountActual': 100.0,
            'toAmountActual': 95.0,
            'details': 'Test notification'
        }
        
        process_message(mock_message)
        return {"message": "Notification sent"}, 200

@notification_ns.route('/sms')
class SMS(Resource):
    @notification_ns.expect(sms_model)
    @notification_ns.doc(description="Send SMS notification directly")
    def post(self):
        """Send SMS notification directly"""
        data = request.json
        result = send_sms(data.get('mobile'), data.get('message'))
        if result:
            return {"message": "SMS sent successfully", "result": result}, 200
        return {"message": "Failed to send SMS"}, 500

@notification_ns.route('/email')
class Email(Resource):
    @notification_ns.expect(email_model)
    @notification_ns.doc(description="Send email notification directly")
    def post(self):
        """Send email notification directly"""
        data = request.json
        success = send_email(data.get('to'), data.get('subject'), data.get('body'))
        if success:
            return {"message": "Email sent successfully"}, 200
        return {"message": "Failed to send email"}, 500

# Add namespaces to API
api.add_namespace(notification_ns)
api.add_namespace(transaction_ns)

if __name__ == '__main__':
    # Connect to RabbitMQ
    if connect_amqp():
        # Start AMQP consumer in a separate thread
        threading.Thread(target=start_consumer, daemon=True).start()
    else:
        logger.warning("Could not connect to RabbitMQ. Notification service will run without messaging capability.")
    
    # Start Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)