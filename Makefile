.PHONY: all certs server-certs client-certs rabbitmq-pod-start rabbitmq-pod-stop rabbitmq-pod-rm rabbitmq-setup-permissions rabbitmq-setup-topology rabbitmq-logs producer consumer clean hosts-check requirements help print-rabbitmq-fqdn print-container-name

# Variables
PODMAN_IMAGE_NAME = rabbitmq:4.1-management
CONTAINER_NAME = rabbitmq-dev-server
RABBITMQ_FQDN = rabbitmq.labs.dontesta.it
VHOST_NAME = logistics_vhost
RABBITMQ_DEFAULT_USER = rabbitmq
RABBITMQ_DEFAULT_PASS = rabbitmq

# Administrator user for topology configuration
RABBITMQ_ADMIN_USER = rabbit_admin
RABBITMQ_ADMIN_PASS = 'SuperS3cureAdminP@ssw0rd!'

RABBITMQ_LOG = debug
PRODUCER_USER = order_sender
PRODUCER_PASSWORD = 'OrderSenderP@ssw0rd'
CONSUMER_USER = delivery_receiver
CONSUMER_PASSWORD = 'DeliveryReceiverP@ssw0rd'

# Certificate settings
CERTS_DIR = certs
CA_KEY = $(CERTS_DIR)/ca.key
CA_CERT = $(CERTS_DIR)/ca.pem
SERVER_KEY = $(CERTS_DIR)/server.key
SERVER_CSR = $(CERTS_DIR)/server.csr
SERVER_CERT = $(CERTS_DIR)/server.pem
SERVER_EXT = $(CERTS_DIR)/server.ext
PRODUCER_KEY = $(CERTS_DIR)/order_sender_client.key
PRODUCER_CSR = $(CERTS_DIR)/order_sender_client.csr
PRODUCER_CERT = $(CERTS_DIR)/order_sender_client.pem
CONSUMER_KEY = $(CERTS_DIR)/delivery_receiver_client.key
CONSUMER_CSR = $(CERTS_DIR)/delivery_receiver_client.csr
CONSUMER_CERT = $(CERTS_DIR)/delivery_receiver_client.pem

# Subject settings
CA_SUBJECT = "/C=IT/ST=Sicilia/L=Bronte/O=Dontesta/OU=DevOps/CN=Dontesta-CA"
SERVER_SUBJECT = "/C=IT/ST=Sicilia/L=Bronte/O=Dontesta/OU=RabbitMQServer/CN=${RABBITMQ_FQDN}"
PRODUCER_SUBJECT = "/C=IT/ST=Sicilia/L=Bronte/O=Dontesta/OU=Client/CN=order_sender_client"
CONSUMER_SUBJECT = "/C=IT/ST=Sicilia/L=Bronte/O=Dontesta/OU=Client/CN=delivery_receiver_client"

# ANSI color codes
YELLOW = \033[1;33m
NC = \033[0m # No Color

# Default target
all: certs rabbitmq-pod-start rabbitmq-setup-permissions rabbitmq-setup-topology

# Check /etc/hosts
hosts-check:
	@echo "Checking /etc/hosts for entry '127.0.0.1 ${RABBITMQ_FQDN}'..."
	@if ! grep -q "${RABBITMQ_FQDN}" /etc/hosts; then \
		echo "ERROR: Add '127.0.0.1 ${RABBITMQ_FQDN}' to /etc/hosts"; \
		exit 1; \
	fi
	@echo "/etc/hosts is OK."

# Generate all TLS certificates
certs: server-certs client-certs
	@echo "All certificates generated in ./$(CERTS_DIR)/"

server-certs:
	@echo "Generating CA and Server certificates..."
	@mkdir -p $(CERTS_DIR)
	@if [ -f "$(CA_KEY)" ]; then echo "$(YELLOW)WARNING: $(CA_KEY) already exists and will be overwritten.$(NC)"; fi
	@if [ -f "$(CA_CERT)" ]; then echo "$(YELLOW)WARNING: $(CA_CERT) already exists and will be overwritten.$(NC)"; fi
	@if [ -f "$(SERVER_KEY)" ]; then echo "$(YELLOW)WARNING: $(SERVER_KEY) already exists and will be overwritten.$(NC)"; fi
	@if [ -f "$(SERVER_CERT)" ]; then echo "$(YELLOW)WARNING: $(SERVER_CERT) already exists and will be overwritten.$(NC)"; fi
	@echo 'authorityKeyIdentifier=keyid,issuer\nbasicConstraints=CA:FALSE\nkeyUsage = digitalSignature, nonRepudiation, keyEncipherment, dataEncipherment\nsubjectAltName = @alt_names\n\n[alt_names]\nDNS.1 = ${RABBITMQ_FQDN}\nDNS.2 = localhost\nIP.1 = 127.0.0.1' > $(SERVER_EXT)
	@openssl genrsa -out $(CA_KEY) 4096 > /dev/null 2>&1
	@openssl req -x509 -new -nodes -key $(CA_KEY) -sha256 -days 1024 -out $(CA_CERT) \
		-subj "$(CA_SUBJECT)" > /dev/null 2>&1
	@openssl genrsa -out $(SERVER_KEY) 2048 > /dev/null 2>&1
	@openssl req -new -key $(SERVER_KEY) -out $(SERVER_CSR) \
		-subj "$(SERVER_SUBJECT)" > /dev/null 2>&1
	@openssl x509 -req -in $(SERVER_CSR) -CA $(CA_CERT) -CAkey $(CA_KEY) -CAcreateserial \
		-out $(SERVER_CERT) -days 500 -sha256 -extfile $(SERVER_EXT) > /dev/null 2>&1
	@echo "CA and Server certificates generated."

client-certs: $(CA_CERT) $(CA_KEY) # Depends on the CA
	@echo "Generating Client certificates (Producer and Consumer)..."
	@if [ -f "$(PRODUCER_KEY)" ]; then echo "$(YELLOW)WARNING: $(PRODUCER_KEY) already exists and will be overwritten.$(NC)"; fi
	@if [ -f "$(PRODUCER_CERT)" ]; then echo "$(YELLOW)WARNING: $(PRODUCER_CERT) already exists and will be overwritten.$(NC)"; fi
	@if [ -f "$(CONSUMER_KEY)" ]; then echo "$(YELLOW)WARNING: $(CONSUMER_KEY) already exists and will be overwritten.$(NC)"; fi
	@if [ -f "$(CONSUMER_CERT)" ]; then echo "$(YELLOW)WARNING: $(CONSUMER_CERT) already exists and will be overwritten.$(NC)"; fi
	@# Producer Client Cert
	@openssl genrsa -out $(PRODUCER_KEY) 2048 > /dev/null 2>&1
	@openssl req -new -key $(PRODUCER_KEY) -out $(PRODUCER_CSR) \
		-subj "$(PRODUCER_SUBJECT)" > /dev/null 2>&1
	@openssl x509 -req -in $(PRODUCER_CSR) -CA $(CA_CERT) -CAkey $(CA_KEY) -CAcreateserial \
		-out $(PRODUCER_CERT) -days 365 -sha256 > /dev/null 2>&1
	@echo "Producer client certificate generated: $(PRODUCER_CERT)"
	@# Consumer Client Cert
	@openssl genrsa -out $(CONSUMER_KEY) 2048 > /dev/null 2>&1
	@openssl req -new -key $(CONSUMER_KEY) -out $(CONSUMER_CSR) \
		-subj "$(CONSUMER_SUBJECT)" > /dev/null 2>&1
	@openssl x509 -req -in $(CONSUMER_CSR) -CA $(CA_CERT) -CAkey $(CA_KEY) -CAcreateserial \
		-out $(CONSUMER_CERT) -days 365 -sha256 > /dev/null 2>&1
	@echo "Consumer client certificate generated: $(CONSUMER_CERT)"
	@echo "Client certificates generated."

# Start RabbitMQ container
rabbitmq-pod-start: hosts-check
	@echo "Starting RabbitMQ container (${CONTAINER_NAME}) with image ${PODMAN_IMAGE_NAME}..."
	@if ! podman container exists $(CONTAINER_NAME); then \
		podman run -d --name ${CONTAINER_NAME} \
			--hostname ${RABBITMQ_FQDN} \
			-p 5671:5671 \
			-p 15672:15672 \
			-e RABBITMQ_DEFAULT_USER=${RABBITMQ_DEFAULT_USER} \
			-e RABBITMQ_DEFAULT_PASS=${RABBITMQ_DEFAULT_PASS} \
			-e RABBITMQ_LOG=${RABBITMQ_LOG} \
			-v $(CURDIR)/certs:/etc/rabbitmq/certs:ro,z \
			-v $(CURDIR)/rabbitmq_config/rabbitmq.conf:/etc/rabbitmq/rabbitmq.conf:ro,z \
			-v rabbitmq_data:/var/lib/rabbitmq:z \
			${PODMAN_IMAGE_NAME}; \
		echo "Container started. Waiting 5 seconds for initialization..."; \
		sleep 5; \
	else \
		echo "Container ${CONTAINER_NAME} already exists. If stopped, try 'make rabbitmq-pod-restart'"; \
		podman start ${CONTAINER_NAME}; \
		echo "Waiting 5 seconds for restart..."; \
		sleep 5; \
	fi

# Stop RabbitMQ container
rabbitmq-pod-stop:
	@echo "Stopping RabbitMQ container (${CONTAINER_NAME})..."
	@podman stop ${CONTAINER_NAME} || echo "Container already stopped or does not exist."

# Remove RabbitMQ container
rabbitmq-pod-rm: rabbitmq-pod-stop
	@echo "Removing RabbitMQ container (${CONTAINER_NAME})..."
	@podman rm ${CONTAINER_NAME} || echo "Container does not exist."
	@echo "Removing RabbitMQ data volume (if not used by other containers)..."
	@podman volume rm rabbitmq_data || echo "Volume does not exist or is in use."

# Restart RabbitMQ container
rabbitmq-pod-restart: rabbitmq-pod-stop rabbitmq-pod-start

# Configure vhost and permissions
rabbitmq-setup-permissions:
	@echo "Configuring RabbitMQ vhost, users, and permissions..."
	@sleep 5
	podman exec ${CONTAINER_NAME} rabbitmqctl add_vhost ${VHOST_NAME} || echo "Vhost ${VHOST_NAME} already exists."
	@echo "Creating admin user: ${RABBITMQ_ADMIN_USER}"
	podman exec ${CONTAINER_NAME} rabbitmqctl add_user ${RABBITMQ_ADMIN_USER} ${RABBITMQ_ADMIN_PASS} || echo "User ${RABBITMQ_ADMIN_USER} already exists."
	podman exec ${CONTAINER_NAME} rabbitmqctl set_user_tags ${RABBITMQ_ADMIN_USER} administrator
	podman exec ${CONTAINER_NAME} rabbitmqctl set_permissions -p ${VHOST_NAME} ${RABBITMQ_ADMIN_USER} ".*" ".*" ".*"
	@echo "Creating application users..."
	podman exec ${CONTAINER_NAME} rabbitmqctl add_user ${PRODUCER_USER} ${PRODUCER_PASSWORD} || echo "User ${PRODUCER_USER} already exists."
	podman exec ${CONTAINER_NAME} rabbitmqctl add_user ${CONSUMER_USER} ${CONSUMER_PASSWORD} || echo "User ${CONSUMER_USER} already exists."
	@echo "Setting permissions for application users on vhost ${VHOST_NAME}..."
	podman exec ${CONTAINER_NAME} rabbitmqctl set_permissions -p ${VHOST_NAME} ${PRODUCER_USER} "" "^order_exchange$$" ""
	podman exec ${CONTAINER_NAME} rabbitmqctl set_permissions -p ${VHOST_NAME} ${CONSUMER_USER} "" "" "^logistics_queue$$"
	@echo "Vhost, users, and permissions configured."

# Configure exchange, queue, and binding
rabbitmq-setup-topology:
	@echo "Configuration topology RabbitMQ (exchange, queue, binding) with user ${RABBITMQ_ADMIN_USER}..."
	@sleep 2
	podman exec ${CONTAINER_NAME} rabbitmqadmin -u ${RABBITMQ_ADMIN_USER} -p ${RABBITMQ_ADMIN_PASS} -V ${VHOST_NAME} declare exchange name=order_exchange type=direct durable=true || echo "Exchange order_exchange already exists or error."
	podman exec ${CONTAINER_NAME} rabbitmqadmin -u ${RABBITMQ_ADMIN_USER} -p ${RABBITMQ_ADMIN_PASS} -V ${VHOST_NAME} declare queue name=logistics_queue durable=true || echo "Queue logistics_queue already exists or error."
	podman exec ${CONTAINER_NAME} rabbitmqadmin -u ${RABBITMQ_ADMIN_USER} -p ${RABBITMQ_ADMIN_PASS} -V ${VHOST_NAME} declare binding source="order_exchange" destination_type="queue" destination="logistics_queue" routing_key="new_order_event" || echo "Binding already exists or error."
	@echo "Topology configured."

# Show RabbitMQ logs
rabbitmq-logs:
	@echo "Showing logs for RabbitMQ container (${CONTAINER_NAME}):"
	podman logs -f ${CONTAINER_NAME}

# Run producer script
producer:
	@echo "Running Producer Python script..."
	@export PRODUCER_PASSWORD=${PRODUCER_PASSWORD}; python producer.py

# Run consumer script
consumer:
	@echo "Running Consumer Python script..."
	@export CONSUMER_PASSWORD=${CONSUMER_PASSWORD}; python consumer.py

# Clean up
clean: rabbitmq-pod-rm
	@echo "Cleaning up generated certificates and configuration files..."
	@rm -rf certs
	@rm -f *.srl
	@echo "Cleanup completed."

# Create requirements.txt
requirements:
	@echo "Creating requirements.txt..."
	@echo "python-qpid-proton" > requirements.txt
	@echo "python-dotenv" >> requirements.txt
	@echo "requirements.txt created. Install with: pip install -r requirements.txt"

# Print RabbitMQ FQDN
print-rabbitmq-fqdn:
	@echo $(RABBITMQ_FQDN)

# Print container name
print-container-name:
	@echo $(CONTAINER_NAME)

# Help command
help:
	@echo ""
	@echo "Available commands in Makefile:"
	@echo ""
	@echo "  all                        Generate certificates, start RabbitMQ, configure permissions and topology"
	@echo "  certs                      Generate all certificates needed for mTLS"
	@echo "  clean                      Remove certificates, keys, and RabbitMQ container"
	@echo "  server-certs               Generate only CA and server certificates"
	@echo "  client-certs               Generate only client certificates (producer and consumer)"
	@echo "  hosts-check                Check for FQDN presence in /etc/hosts"
	@echo "  rabbitmq-pod-start         Start RabbitMQ container with mTLS"
	@echo "  rabbitmq-pod-stop          Stop RabbitMQ container"
	@echo "  rabbitmq-pod-rm            Stop and remove RabbitMQ container and data volume"
	@echo "  rabbitmq-pod-restart       Restart RabbitMQ container"
	@echo "  rabbitmq-setup-permissions Configure vhost, users, and permissions in RabbitMQ"
	@echo "  rabbitmq-setup-topology    Create necessary exchanges, queues, and bindings"
	@echo "  rabbitmq-logs              Show RabbitMQ container logs"
	@echo "  producer                   Run Python producer script"
	@echo "  consumer                   Run Python consumer script"
	@echo "  requirements               Create requirements.txt for pip"
	@echo "  print-rabbitmq-fqdn        Print the RabbitMQ FQDN"
	@echo "  print-container-name       Print the RabbitMQ container name"
	@echo ""
	@echo "Usage example:"
	@echo "  make all"
	@echo "  make producer"
	@echo "  make consumer"
	@echo ""