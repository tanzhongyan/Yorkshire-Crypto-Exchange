"""
Reusable AMQP-related functions for Flask microservices

Handles robust connection, exchange/queue declaration, and message consumption.
"""

import time
import pika
from pika.exceptions import (
    AMQPConnectionError,
    ChannelClosedByBroker,
    ConnectionClosedByBroker,
    AMQPError,
)


def connect(hostname, port, exchange_name, exchange_type, max_retries=12, retry_interval=5):
    retries = 0
    while retries < max_retries:
        retries += 1
        try:
            print(f"Connecting to RabbitMQ at {hostname}:{port} (attempt {retries})")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(
                    host=hostname,
                    port=port,
                    heartbeat=300,
                    blocked_connection_timeout=300
                )
            )
            channel = connection.channel()
            print(f"Checking existence of exchange: {exchange_name}")
            channel.exchange_declare(exchange=exchange_name, exchange_type=exchange_type, passive=True)
            return connection, channel
        except ChannelClosedByBroker as e:
            message = f"{exchange_type} exchange '{exchange_name}' not found."
            raise Exception(message) from e
        except AMQPConnectionError as e:
            print(f"[!] Connection failed: {e}, retrying in {retry_interval}s...")
            time.sleep(retry_interval)

    raise Exception(f"Exceeded max retries ({max_retries}) trying to connect to RabbitMQ.")


def is_connection_open(connection):
    try:
        connection.process_data_events()
        return True
    except AMQPError as e:
        print("AMQP Error:", e)
        return False


def close(connection, channel):
    if channel and channel.is_open:
        channel.close()
    if connection and connection.is_open:
        connection.close()


def start_consuming(
    hostname,
    port,
    exchange_name,
    exchange_type,
    queue_name,
    callback,
    routing_key=None,
    durable=True,
    retry_interval=5,
):
    while True:
        try:
            connection, channel = connect(
                hostname=hostname,
                port=port,
                exchange_name=exchange_name,
                exchange_type=exchange_type
            )

            print(f"Declaring queue: {queue_name}")
            channel.queue_declare(queue=queue_name, durable=durable)

            if routing_key:
                print(f"Binding queue to exchange with routing key: {routing_key}")
                channel.queue_bind(exchange=exchange_name, queue=queue_name, routing_key=routing_key)

            print(f"[*] Now consuming from queue: {queue_name}")
            channel.basic_consume(
                queue=queue_name,
                on_message_callback=callback,
                auto_ack=True
            )

            channel.start_consuming()

        except ChannelClosedByBroker as e:
            raise Exception(f"Queue '{queue_name}' not found.") from e

        except ConnectionClosedByBroker:
            print("[!] Connection closed by broker. Reconnecting...")
            time.sleep(retry_interval)
            continue

        except KeyboardInterrupt:
            print("[x] Gracefully stopping...")
            close(connection, channel)
            break

        except Exception as e:
            print(f"[!] Unhandled exception: {e}")
            time.sleep(retry_interval)
