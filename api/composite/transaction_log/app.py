from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import pika
import json
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://user:password@localhost/transaction_db'
db = SQLAlchemy(app)

class TransactionLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.String, nullable=False)
    selling_wallet_id = db.Column(db.String, nullable=False)
    base_token = db.Column(db.String, nullable=False)
    quote_token = db.Column(db.String, nullable=False)
    order_quantity = db.Column(db.Float, nullable=False)
    limit_price = db.Column(db.Float, nullable=False)
    order_id = db.Column(db.String, unique=True, nullable=False)
    time_created = db.Column(db.DateTime, default=datetime.utcnow)
    time_closed = db.Column(db.DateTime, nullable=True)

# RabbitMQ Connection
def send_to_queue(message):
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))
    channel = connection.channel()
    channel.queue_declare(queue='transaction_logs')
    channel.basic_publish(exchange='', routing_key='transaction_logs', body=json.dumps(message))
    connection.close()

@app.route('/v1/api/transaction-logs', methods=['GET'])
def get_all_logs():
    logs = TransactionLog.query.all()
    return jsonify([log.__dict__ for log in logs])

@app.route('/api/v1/transactions-logs', methods=['POST'])
def create_log():
    data = request.json
    new_log = TransactionLog(**data)
    db.session.add(new_log)
    db.session.commit()
    send_to_queue(data)
    return jsonify({"message": "Transaction log created"}), 201

@app.route('/api/v1/transactions-logs/<order_id>', methods=['PUT'])
def update_log(order_id):
    log = TransactionLog.query.filter_by(order_id=order_id).first()
    if not log:
        return jsonify({"error": "Transaction log not found"}), 404
    
    for key, value in request.json.items():
        setattr(log, key, value)
    
    db.session.commit()
    send_to_queue(request.json)
    return jsonify({"message": "Transaction log updated"})

@app.route('/api/v1/transactions-logs/<order_id>', methods=['DELETE'])
def delete_log(order_id):
    log = TransactionLog.query.filter_by(order_id=order_id).first()
    if not log:
        return jsonify({"error": "Transaction log not found"}), 404
    
    db.session.delete(log)
    db.session.commit()
    send_to_queue({"order_id": order_id, "message": "Deleted"})
    return jsonify({"message": "Transaction log deleted"})

import json

def seed_data():
    with open('seeddata.json') as f:
        data = json.load(f)
        for entry in data:
            transaction = TransactionLog(**entry)
            db.session.add(transaction)
        db.session.commit()
        print("Seed data inserted successfully.")

if __name__ == '__main__':
    db.create_all()
    seed_data()
    app.run(debug=True)
