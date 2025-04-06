import pika

amqp_host = "rabbitmq"
amqp_port = 5672
exchange_name = "order_topic"
exchange_type = "topic"


def create_exchange(hostname, port, exchange_name, exchange_type):
    print(f"Connecting to AMQP broker {hostname}:{port}...")
    # connect to the broker
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=hostname,
            port=port,
            heartbeat=300,
            blocked_connection_timeout=300,
        )
    )
    print("Connected")

    print("Open channel")
    channel = connection.channel()

    # Set up the exchange if the exchange doesn't exist
    print(f"Declare exchange: {exchange_name}")
    channel.exchange_declare(
        exchange=exchange_name, exchange_type=exchange_type, durable=True
    )
    # 'durable' makes the exchange survive broker restarts

    return channel


def create_queue(channel, exchange_name, queue_name, routing_key):
    print(f"Bind to queue: {queue_name}")
    channel.queue_declare(queue=queue_name, durable=True)
    # 'durable' makes the queue survive broker restarts

    # bind the queue to the exchange via the routing_key
    channel.queue_bind(
        exchange=exchange_name, queue=queue_name, routing_key=routing_key
    )


channel = create_exchange(
    hostname=amqp_host,
    port=amqp_port,
    exchange_name=exchange_name,
    exchange_type=exchange_type,
)

# (1) order management service publishes, orderbook service consumes
create_queue(
    channel=channel,
    exchange_name=exchange_name,
    queue_name="order_initiation_service.orders_creation",
    routing_key="order.new",
)

# (2) NIL orderbook service publishes, order management service consumes
create_queue(
    channel=channel,
    exchange_name=exchange_name,
    queue_name="orderbook_service.orders_placed",
    routing_key="order.executed",
)

# (3) orderbook service publishes, order completion service consumes
# create_queue(
#     channel=channel,
#     exchange_name=exchange_name,
#     queue_name="order_completion_service.orders_placed",
#     routing_key="order.executed",
# )
