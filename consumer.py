"""
AMQP 1.0 mTLS Consumer for RabbitMQ.

This script connects to a RabbitMQ broker using AMQP 1.0 over mTLS,
authenticates with a client certificate, and consumes messages from a specified queue.
It uses the python-qpid-proton library for AMQP 1.0 communication.

Environment variables are used for configuration, with defaults provided.
- RABBITMQ_HOST: The hostname or IP address of the RabbitMQ broker.
- RABBITMQ_PORT: The port number for AMQP 1.0 with TLS (default 5671).
- VHOST: The virtual host to connect to, in Proton format (e.g., "vhost:my_vhost").
- CONSUMER_USER: The username for authentication.
- CONSUMER_PASSWORD: The password for authentication.
- SOURCE_NODE: The AMQP source address (e.g., "/queues/my_queue").
- Certificate paths (CA_CERT_PATH, CONSUMER_CLIENT_CERT_PATH, CONSUMER_CLIENT_KEY_PATH)
  are derived relative to this script's location, assuming a 'certs/' subdirectory.
"""
import json
import os
import time
from dotenv import load_dotenv

from proton import SSLDomain, Delivery
from proton.handlers import MessagingHandler
from proton.reactor import Container

load_dotenv()

RABBITMQ_HOST = os.getenv("RABBITMQ_HOST", "rabbitmq.labs.dontesta.it")
RABBITMQ_PORT = int(os.getenv("RABBITMQ_PORT", 5671))
VHOST_NAME_ONLY = "logistics_vhost" # Pure vhost name
VHOST_PROTON_FORMAT = f"vhost:{VHOST_NAME_ONLY}" # Format for Proton
VHOST = os.getenv("VHOST", VHOST_PROTON_FORMAT) # Use the correct format
CONSUMER_USER = os.getenv("CONSUMER_USER", "delivery_receiver")
CONSUMER_PASSWORD = os.getenv("CONSUMER_PASSWORD", "DeliveryReceiverP@ssw0rd")

# Certificate paths for mTLS (use absolute paths)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CA_CERT_PATH = os.path.join(BASE_DIR, "certs/ca.pem")
CONSUMER_CLIENT_CERT_PATH = os.path.join(BASE_DIR, "certs/delivery_receiver_client.pem")
CONSUMER_CLIENT_KEY_PATH = os.path.join(BASE_DIR, "certs/delivery_receiver_client.key")
# CONSUMER_CLIENT_KEY_PASSWORD = None # If the client key is password-protected

SOURCE_NODE = os.getenv("SOURCE_NODE", "/queues/logistics_queue")
CONNECTION_URL = f"amqps://{RABBITMQ_HOST}:{RABBITMQ_PORT}"

class OrderConsumer(MessagingHandler):
    """
    A Qpid Proton MessagingHandler for consuming order messages from RabbitMQ.

    This class handles AMQP 1.0 events to establish an mTLS connection,
    create a receiver link, process incoming messages, and manage errors.
    """
    def __init__(self, server_url, source_address):
        """
        Initializes the OrderConsumer.

        Args:
            server_url (str): The AMQP connection URL (e.g., "amqps://host:port").
            source_address (str): The AMQP source node address (e.g., "/queues/my_queue").
        """
        super(OrderConsumer, self).__init__()
        self.server_url = server_url
        self.source_address = source_address
        self.receiver = None
        self.received_count = 0

    def on_start(self, event):
        """
        Called when the Qpid Proton reactor starts.

        Configures SSL/TLS for mTLS, establishes a connection to the broker,
        and creates a receiver link to the specified source address.
        Stops the container on SSL configuration or connection failure.

        Args:
            event: The Qpid Proton event object.
        """
        print(f"Consumer: Starting, connecting to {self.server_url}, source: {self.source_address}")

        ssl_domain = SSLDomain(SSLDomain.MODE_CLIENT)
        try:
            ssl_domain.set_peer_authentication(SSLDomain.VERIFY_PEER_NAME)
            ssl_domain.set_trusted_ca_db(CA_CERT_PATH)
            ssl_domain.set_credentials(
                CONSUMER_CLIENT_CERT_PATH,
                CONSUMER_CLIENT_KEY_PATH,
                None # Key password, if needed
            )
            print("Consumer: SSL domain configured successfully.")
        except Exception as e:
            print(f"Consumer: Error during SSL domain configuration: {e}")
            event.container.stop()
            return

        print(f"Consumer: Attempting mTLS connection to {self.server_url} with user {CONSUMER_USER} on vhost {VHOST}")
        conn = event.container.connect(
            url=self.server_url,
            user=CONSUMER_USER,
            password=CONSUMER_PASSWORD,
            virtual_host=VHOST,
            sni=RABBITMQ_HOST,
            ssl_domain=ssl_domain,
            allow_insecure_mechs=False,
            allowed_mechs="PLAIN"
        )
        if conn:
            print(f"Consumer: mTLS connection initiated, vhost set to {VHOST}")
            self.receiver = event.container.create_receiver(conn, self.source_address)
            if self.receiver:
                print(f"Consumer: Receiver created for source '{self.source_address}'")
            else:
                print(f"Consumer: Error: create_receiver() returned None for source '{self.source_address}'. Verify that the source exists and is accessible.")
                if conn: conn.close()
                event.container.stop()
        else:
            print("Consumer: Error: connect() returned None.")
            event.container.stop()

    def on_message(self, event):
        """
        Called when a message is received on the receiver link.

        Processes the incoming message, decodes its JSON body,
        and accepts, rejects, or releases the message based on processing outcome.

        Args:
            event: The Qpid Proton event object containing the message.
        """
        if event.receiver == self.receiver:
            message = event.message
            delivery = event.delivery
            self.received_count += 1
            print("-" * 20)
            print(f"Consumer: New message received! (Total: {self.received_count})")
            try:
                message_body_str = message.body
                if isinstance(message_body_str, bytes):
                    message_body_str = message_body_str.decode('utf-8')
                order_data = json.loads(message_body_str)
                print(f"Consumer: Content: {order_data}")
                time.sleep(0.2) # Simulate some processing time
                print("Consumer: Order processed.")
                delivery.update(Delivery.ACCEPTED)
                print("Consumer: Message confirmed (accepted).")
            except json.JSONDecodeError:
                print(f"Consumer: JSON Error: {message.body}")
                delivery.update(Delivery.REJECTED)
                print("Consumer: Message rejected.")
            except Exception as e:
                print(f"Consumer: Processing error: {e}")
                delivery.update(Delivery.RELEASED)
                print("Consumer: Message released.")
            print("-" * 20)

    def on_disconnected(self, event):
        """
        Called when the connection to the broker is disconnected.

        This can occur due to normal shutdown (e.g., KeyboardInterrupt) or an error.
        Stops the Qpid Proton container.

        Args:
            event: The Qpid Proton event object.
        """
        print(f"Consumer: Disconnected from {self.server_url}")
        print("Consumer: Attempting to stop the container.")
        event.container.stop()

    def on_transport_error(self, event):
        """
        Called when a transport-level error occurs (e.g., SSL/TLS handshake failure).

        Logs the error and stops the Qpid Proton container.

        Args:
            event: The Qpid Proton event object.
        """
        condition = event.transport.condition
        print(f"Consumer: Transport error (mTLS?): {condition if condition else 'N/A'}")
        if event.connection: event.connection.close()
        event.container.stop()

    def on_connection_error(self, event):
        """
        Called when an AMQP connection-level error occurs.

        Logs the error and stops the Qpid Proton container.

        Args:
            event: The Qpid Proton event object.
        """
        condition = event.connection.remote_condition if event.connection else None
        print(f"Consumer: AMQP connection error (mTLS?): {condition if condition else 'N/A'}")
        if event.connection: event.connection.close()
        event.container.stop()

    def on_link_error(self, event):
        """
        Called when an AMQP link-level error occurs (e.g., receiver link failure).

        Logs the error and stops the Qpid Proton container.

        Args:
            event: The Qpid Proton event object.
        """
        condition = None
        if event.receiver and event.receiver.remote_condition:
            condition = event.receiver.remote_condition
        print(f"Consumer: AMQP link error (receiver): {condition if condition else 'N/A'}")
        if event.connection: event.connection.close()
        event.container.stop()

def receive_order_messages_proton():
    """
    Sets up and runs the Qpid Proton container for the OrderConsumer.

    Initializes the OrderConsumer handler and starts the Proton reactor.
    Handles KeyboardInterrupt for graceful shutdown and other exceptions.
    """
    handler = OrderConsumer(CONNECTION_URL, SOURCE_NODE)
    container = Container(handler)
    try:
        print("Consumer: Starting container to receive messages (Ctrl+C to interrupt)...")
        container.run()
    except KeyboardInterrupt:
        print("\nConsumer: Reception interrupted by user.")
        # The on_disconnected handler should be called, which will stop the container.
        # If not, ensure the container is stopped.
        container.stop()
    except Exception as e:
        print(f"Consumer: Critical error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("Consumer: Container execution finished.")

if __name__ == "__main__":
    receive_order_messages_proton()