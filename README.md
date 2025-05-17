# RabbitMQ 4.1 mTLS and AMQP 1.0 - Proof of Concept

[![Antonio Musarra's Blog](https://img.shields.io/badge/maintainer-Antonio_Musarra's_Blog-purple.svg?colorB=6e60cc)](https://www.dontesta.it)
[![Keep a Changelog v1.1.0 badge](https://img.shields.io/badge/changelog-Keep%20a%20Changelog%20v1.1.0-%23E05735)](CHANGELOG.md)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[![CI Build and Test](https://github.com/amusarra/rabbitmq-mtls-poc/actions/workflows/ci.yml/badge.svg)](https://github.com/amusarra/rabbitmq-mtls-poc/actions/workflows/ci.yml)

This project is a Proof of Concept (PoC) that demonstrates how to configure a RabbitMQ 4.1 (or later) environment to use mutual TLS authentication (mTLS) and the AMQP 1.0 protocol. The goal is to provide a practical guide and a development scenario that closely mirrors secure production configurations.

## Main Features

* **Advanced Security (mTLS)**: Configuration of RabbitMQ to require and verify client certificates, ensuring that only authorized clients can connect. Both the RabbitMQ server and the clients authenticate each other.
* **Modern Protocol (AMQP 1.0)**: Use of the AMQP 1.0 protocol for interoperability and advanced features, natively supported by RabbitMQ 4.0+.
* **Automation with Makefile**: A comprehensive `Makefile` to automate:
  * Generation of a local CA and server/client certificates.
  * Starting and managing a RabbitMQ container (via Podman) with mTLS configuration.
  * Configuration of vhost, users, permissions, and topology (exchange, queue, binding) in RabbitMQ.
* **Python Examples (Producer/Consumer)**: Example Python scripts using the `python-qpid-proton` library to demonstrate sending and receiving messages in an mTLS and AMQP 1.0 environment.
* **FQDN Configuration**: Use of Fully Qualified Domain Names (FQDN) and Subject Alternative Names (SAN) for certificates, simulating a real-world scenario.
* **Detailed Documentation**: A practical guide (in `docs/blog/`) explaining the concepts and configuration steps.

## Project Objectives

* Provide a local development environment that closely simulates a secure production configuration for RabbitMQ.
* Show how to implement AMQP 1.0 clients in Python that interact with a RabbitMQ broker protected by mTLS.
* Simplify the setup and configuration process through automation.
* Highlight critical points and best practices in configuring mTLS, SNI, and virtual hosts with RabbitMQ and Proton.

## Demo

See the project setup and execution in action:

[Watch a demo of the project in action](https://www.dontesta.it/wp-content/uploads/2020/11/registrazione_demo_setup_env_rabbitmq_41_mtls_1.gif)

## Prerequisites

Refer to the "Prerequisites" section in the [detailed guide](docs/blog/configurare_rabbitmq_41_mtls_guida_pratica_dev.md) (Note: this link points to an Italian document, you might want to translate it or create an English version).

## Getting Started

1. **Clone the repository:**

    ```bash
    git clone https://github.com/amusarra/rabbitmq-mtls-poc.git
    cd rabbitmq-mtls-poc
    ```

2. **Verify prerequisites** (Podman, OpenSSL, Python, etc.).

3. **Configure `/etc/hosts`** (if necessary, as described in the guide).

4. **Generate certificates, start RabbitMQ, and configure everything:**

    ```bash
    make all
    ```

    This command will take care of the entire initial setup.

5. **Install Python dependencies** (preferably in a virtual environment):

    ```bash
    make requirements
    pip install -r requirements.txt
    ```

6. **Run the example scripts:**
    * In one terminal, start the producer:
  
        ```bash
        make producer
        ```

    * In another terminal, start the consumer:
  
        ```bash
        make consumer
        ```

7. **Consult the documentation** for more details on configuration and concepts:
    * [Configuring RabbitMQ 4.1 mTLS and AMQP 1.0: A Practical Guide for Developers](docs/blog/configurare_rabbitmq_41_mtls_guida_pratica_dev.md) (Note: this link points to an Italian document)

## Project Structure

Refer to the "Project Structure" section in the [detailed guide](docs/blog/configurare_rabbitmq_41_mtls_guida_pratica_dev.md) (Note: this link points to an Italian document).

## Useful Makefile Commands

* `make help`: Shows all available targets and configurable variables.
* `make clean`: Removes generated certificates and stops/removes the RabbitMQ container.
* `make rabbitmq-logs`: Shows the RabbitMQ container logs.

## License

This project is released under the MIT License. See the [LICENSE.md](LICENSE.md) file for more details.
