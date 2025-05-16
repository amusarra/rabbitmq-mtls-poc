import json
import os
import random
import uuid # To generate unique order_ids
from dotenv import load_dotenv

from proton import Message, SSLDomain
from proton.handlers import MessagingHandler
from proton.reactor import Container

load_dotenv()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq.labs.dontesta.it")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5671))
VHOST_NAME_ONLY = "logistics_vhost" # Pure vhost name
VHOST_PROTON_FORMAT = f"vhost:{VHOST_NAME_ONLY}" # Format for Proton
VHOST = os.getenv("VHOST", VHOST_PROTON_FORMAT) # Use the correct format
PRODUCER_USER = os.getenv("PRODUCER_USER", "order_sender")
PRODUCER_PASSWORD = os.getenv("PRODUCER_PASSWORD", "OrderSenderP@ssw0rd")

# Certificate paths for mTLS
# Ensure these paths are correct or use absolute paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CA_CERT_PATH = os.path.join(BASE_DIR, "certs/ca.pem")
PRODUCER_CLIENT_CERT_PATH = os.path.join(BASE_DIR, "certs/order_sender_client.pem")
PRODUCER_CLIENT_KEY_PATH = os.path.join(BASE_DIR, "certs/order_sender_client.key")
# PRODUCER_CLIENT_KEY_PASSWORD = None # If the client key is password-protected

TARGET_NODE = os.getenv("TARGET_NODE", "/exchanges/order_exchange/new_order_event")
CONNECTION_URL = f"amqps://{RABBITMQ_HOST}:{RABBITMQ_PORT}/"

# --- Configuration for random order generation ---
NUM_ORDERS_TO_SEND = int(os.getenv("NUM_ORDERS_TO_SEND", 5)) # Number of orders to generate
POSSIBLE_ITEMS = [
    {"id_prefix": "ITEM_A", "description": "Amazing Widget"},
    {"id_prefix": "ITEM_B", "description": "Brilliant Gadget"},
    {"id_prefix": "ITEM_C", "description": "Cool Gizmo"},
    {"id_prefix": "ITEM_D", "description": "Durable Device"},
    {"id_prefix": "ITEM_E", "description": "Elegant Contraption"}
]
MAX_QUANTITY = 10
# --- End of order generation configuration ---

class OrderProducer(MessagingHandler):
    def __init__(self, server_url, target_address, orders_to_send):
        super(OrderProducer, self).__init__()
        self.server_url = server_url
        self.target_address = target_address
        self.orders_to_send = orders_to_send
        self.sender = None
        self.sent_count = 0
        self.confirmed_count = 0
        self.total_messages = len(orders_to_send)

    def on_start(self, event):
        print(f"Producer: Starting, connecting to {self.server_url}, target: {self.target_address}")

        ssl_domain = SSLDomain(SSLDomain.MODE_CLIENT)
        try:
            ssl_domain.set_peer_authentication(SSLDomain.VERIFY_PEER_NAME)
            ssl_domain.set_trusted_ca_db(CA_CERT_PATH)
            ssl_domain.set_credentials(
                PRODUCER_CLIENT_CERT_PATH,
                PRODUCER_CLIENT_KEY_PATH,
                None  # Key password, if needed
            )
            print("Producer: SSL domain configured successfully.")
        except Exception as e:
            print(f"Producer: Error during SSL domain configuration: {e}")
            event.container.stop()
            return


        print(f"Producer: Attempting mTLS connection to {self.server_url} with user {PRODUCER_USER} on vhost {VHOST}")
        conn = event.container.connect(
            url=self.server_url,
            user=PRODUCER_USER,
            password=PRODUCER_PASSWORD,
            virtual_host=VHOST,
            sni=RABBITMQ_HOST,
            ssl_domain=ssl_domain,
            allow_insecure_mechs=False,
            allowed_mechs="PLAIN"
        )
        if conn:
            print(f"Producer: mTLS connection initiated, vhost set to {VHOST}")
            self.sender = event.container.create_sender(conn, self.target_address)
            if self.sender:
                print(f"Producer: Sender created for target '{self.target_address}'")
            else:
                print(f"Producer: Error: create_sender() returned None for target '{self.target_address}'. Verify that the target exists and is accessible.")
                if conn: conn.close() # Close the connection if the sender cannot be created
                event.container.stop()
        else:
            print("Producer: Error: connect() returned None.")
            event.container.stop()

    def on_sendable(self, event):
        if self.sender and self.sender.credit and self.sent_count < self.total_messages:
            order_data = self.orders_to_send[self.sent_count]
            message_body = json.dumps(order_data)
            message = Message(body=message_body)
            message.content_type = "application/json"
            # message.subject = "new_order_event" # Optional, if the target does not include the routing key
            self.sender.send(message)
            print(f"Producer: Message sent ({self.sent_count + 1}/{self.total_messages}): {order_data}")
            self.sent_count += 1

    def on_accepted(self, event):
        self.confirmed_count += 1
        print(f"Producer: Message accepted by broker. Confirmed: {self.confirmed_count}/{self.total_messages}")
        if self.confirmed_count == self.total_messages:
            print("Producer: All messages have been confirmed.")
            if event.connection: event.connection.close()
            # The container stops on its own after closing the connection

    def on_rejected(self, event):
        print(f"Producer: Message rejected: {event.delivery.remote_state if event.delivery else 'N/A'}")
        if event.connection: event.connection.close()
        # event.container.stop()

    def on_released(self, event):
        print(f"Producer: Message released: {event.delivery.remote_state if event.delivery else 'N/A'}")
        if event.connection: event.connection.close()
        # event.container.stop()

    def on_disconnected(self, event):
        print(f"Producer: Disconnected from {self.server_url}")
        if self.confirmed_count < self.sent_count:
             print(f"Producer: WARNING - Disconnected before confirmation. Sent: {self.sent_count}, Confirmed: {self.confirmed_count}")
        # Do not call event.container.stop() here if the connection closes normally
        # after on_accepted or in case of a handled error.
        # The container will stop when there are no more active handles or explicit calls.

    def on_transport_error(self, event):
        condition = event.transport.condition
        print(f"Producer: Transport error (mTLS?): {condition if condition else 'N/A'}")
        if event.connection: event.connection.close()
        event.container.stop() # Stop the container in case of a transport error

    def on_connection_error(self, event):
        condition = event.connection.remote_condition if event.connection else None
        print(f"Producer: AMQP connection error (mTLS?): {condition if condition else 'N/A'}")
        if event.connection: event.connection.close()
        event.container.stop() # Stop the container in case of an AMQP connection error

    def on_link_error(self, event):
        condition = None
        if event.sender and event.sender.remote_condition:
            condition = event.sender.remote_condition
        print(f"Producer: AMQP link error (sender): {condition if condition else 'N/A'}")
        if event.connection: event.connection.close()
        event.container.stop() # Stop the container in case of a link error

def generate_random_orders(num_orders):
    orders = []
    for i in range(num_orders):
        item_template = random.choice(POSSIBLE_ITEMS)
        order = {
            "order_id": f"ORD_MTLS_{str(uuid.uuid4())[:8].upper()}", # Unique and shorter order ID
            "item_id": f"{item_template['id_prefix']}_{random.randint(100, 999)}",
            "description": item_template['description'],
            "quantity": random.randint(1, MAX_QUANTITY)
        }
        orders.append(order)
    return orders

def send_order_messages_proton(orders):
    if not orders:
        print("Producer: No orders to send.")
        return
    handler = OrderProducer(CONNECTION_URL, TARGET_NODE, orders)
    container = Container(handler)
    try:
        print(f"Producer: Starting container to send {len(orders)} message(s)...")
        container.run()
        print("Producer: Container execution finished.")
    except Exception as e:
        print(f"Producer: Error during container execution: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    print(f"Producer: Generating {NUM_ORDERS_TO_SEND} random orders...")
    orders_to_send = generate_random_orders(NUM_ORDERS_TO_SEND)
    # print(f"Producer: Orders generated: {orders_to_send}") # Uncomment for debugging
    send_order_messages_proton(orders_to_send)