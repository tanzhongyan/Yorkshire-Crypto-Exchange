import json
import requests
from queue import Queue
from threading import Lock
import amqp_lib

# RabbitMQ Config
RABBIT_HOST = "rabbitmq"
RABBIT_PORT = 5672
EXCHANGE_NAME = "order_topic"
EXCHANGE_TYPE = "topic"
QUEUE_NAME = "notification_service.orders_placed"
ROUTING_KEY = "order.executed"

# External services
TRANSACTION_LOG_SERVICE_URL = "http://transaction-service:5000/api/v1/transaction"
NOTIFICATION_SERVICE_URL = "http://notification-service:5000/api/v1/notify"

# SSE client management
clients = []
lock = Lock()

def event_stream():
    q = Queue()
    with lock:
        clients.append(q)
    try:
        while True:
            data = q.get()
            yield f"data: {data}\n\n"
    except GeneratorExit:
        with lock:
            clients.remove(q)

def publish_update(data):
    msg = json.dumps(data)
    with lock:
        for q in clients:
            q.put(msg)

def update_transaction_log(data):
    try:
        payload = {
            "orderId": data.get("order_id"),
            "userId": data.get("user_id"),
            "type": "order_executed",
            "details": data
        }
        response = requests.post(TRANSACTION_LOG_SERVICE_URL, json=payload)
        print(f"[+] Transaction log updated: {response.status_code}")
    except Exception as e:
        print(f"[!] Failed to update transaction log: {e}")

def send_notification(data):
    try:
        payload = {
            "email": data.get("user_email"),
            "subject": "Your Crypto Order Was Executed",
            "message": f"Order {data.get('order_id')} has been successfully executed."
        }
        response = requests.post(NOTIFICATION_SERVICE_URL, json=payload)
        print(f"[+] Email sent: {response.status_code}")
    except Exception as e:
        print(f"[!] Email sending failed: {e}")

# RabbitMQ callback
def callback(channel, method, properties, body):
    try:
        data = json.loads(body)
        print(f"[x] Received order execution event: {data}")
        update_transaction_log(data)
        publish_update(data)
        send_notification(data)
    except Exception as e:
        print(f"[!] Callback error: {e}")

def start_consumer():
    amqp_lib.start_consuming(
        hostname=RABBIT_HOST,
        port=RABBIT_PORT,
        exchange_name=EXCHANGE_NAME,
        exchange_type=EXCHANGE_TYPE,
        queue_name=QUEUE_NAME,
        callback=callback
    )
