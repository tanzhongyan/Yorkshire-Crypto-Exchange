from flask import Flask, request, Response, Blueprint
from flask_cors import CORS
from flask_restx import Api, Resource, Namespace, fields
import threading
import rabbitmq

# Config
API_VERSION = 'v1'
API_ROOT = f'/api/{API_VERSION}'

app = Flask(__name__)
CORS(app)

blueprint = Blueprint('api', __name__, url_prefix=API_ROOT)
api = Api(blueprint, version=API_VERSION, title='Notification Management Service API',
          description='Composite service for executed orders (SSE + Email + TxLog)')
app.register_blueprint(blueprint)

notification_ns = Namespace('notification', description='Notification endpoints')

notification_model = notification_ns.model("NotificationPayload", {
    "user_email": fields.String(required=True, description="User email"),
    "order_id": fields.String(required=True, description="Order ID")
})

@notification_ns.route('/test-notify')
class TestNotify(Resource):
    @notification_ns.expect(notification_model)
    def post(self):
        """Test endpoint to manually trigger notification"""
        data = request.json
        rabbitmq.send_notification(data)
        return {"message": "Notification sent"}, 200

@notification_ns.route('/stream')
class Stream(Resource):
    def get(self):
        """Stream executed order events (SSE)"""
        return Response(rabbitmq.event_stream(), mimetype='text/event-stream')

@notification_ns.route('/health')
class Health(Resource):
    def get(self):
        return {"message": "Notification Management Service is healthy"}, 200

api.add_namespace(notification_ns)

if __name__ == '__main__':
    threading.Thread(target=rabbitmq.start_consumer, daemon=True).start()
    app.run(host='0.0.0.0', port=5001, debug=True)
