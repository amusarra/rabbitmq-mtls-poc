# RabbitMQ 4.1 mTLS e AMQP 1.0 - Proof of Concept

Questo progetto è un Proof of Concept (PoC) che dimostra come configurare un ambiente RabbitMQ 4.1 (o successivo) per utilizzare la mutua autenticazione TLS (mTLS) e il protocollo AMQP 1.0. L'obiettivo è fornire una guida pratica e uno scenario di sviluppo che rispecchi da vicino le configurazioni di produzione sicure.

## Caratteristiche Principali

* **Sicurezza Avanzata (mTLS)**: Configurazione di RabbitMQ per richiedere e verificare certificati client, garantendo che solo i client autorizzati possano connettersi. Sia il server RabbitMQ che i client si autenticano reciprocamente.
* **Protocollo Moderno (AMQP 1.0)**: Utilizzo del protocollo AMQP 1.0 per l'interoperabilità e le funzionalità avanzate, supportato nativamente da RabbitMQ 4.0+.
* **Automazione con Makefile**: Un `Makefile` completo per automatizzare:
  * Generazione di una CA locale e dei certificati server/client.
  * Avvio e gestione di un container RabbitMQ (tramite Podman) con la configurazione mTLS.
  * Configurazione di vhost, utenti, permessi e topologia (exchange, code, binding) in RabbitMQ.
* **Esempi Python (Producer/Consumer)**: Script Python di esempio che utilizzano la libreria `python-qpid-proton` per dimostrare l'invio e la ricezione di messaggi in un ambiente mTLS e AMQP 1.0.
* **Configurazione FQDN**: Utilizzo di nomi di dominio completi (FQDN) e Subject Alternative Names (SAN) per i certificati, simulando uno scenario reale.
* **Documentazione Dettagliata**: Una guida pratica (in `docs/blog/`) che spiega i concetti e i passaggi di configurazione.

## Obiettivi del Progetto

* Fornire un ambiente di sviluppo locale che simuli da vicino una configurazione di produzione sicura per RabbitMQ.
* Mostrare come implementare client AMQP 1.0 in Python che interagiscono con un broker RabbitMQ protetto da mTLS.
* Semplificare il processo di setup e configurazione tramite automazione.
* Evidenziare i punti critici e le best practice nella configurazione di mTLS, SNI e virtual host con RabbitMQ e Proton.

## Prerequisiti

Consultare la sezione "Prerequisiti" nella [guida dettagliata](docs/blog/configurare_rabbitmq_41_mtls_guida_pratica_dev.md).

## Come Iniziare

1. **Clonare il repository:**

    ```bash
    git clone <URL_DEL_TUO_REPOSITORY>
    cd rabbitmq-mtls-poc
    ```

2. **Verificare i prerequisiti** (Podman, OpenSSL, Python, ecc.).

3. **Configurare `/etc/hosts`** (se necessario, come descritto nella guida).

4. **Generare certificati, avviare RabbitMQ e configurare tutto:**

    ```bash
    make all
    ```

    Questo comando si occuperà di tutto il setup iniziale.

5. **Installare le dipendenze Python** (preferibilmente in un ambiente virtuale):

    ```bash
    make requirements
    pip install -r requirements.txt
    ```

6. **Eseguire gli script di esempio:**
    * In un terminale, avviare il producer:

        ```bash
        make producer
        ```

    * In un altro terminale, avviare il consumer:

        ```bash
        make consumer
        ```

7. **Consultare la documentazione** per maggiori dettagli sulla configurazione e sui concetti:
    * [Configurare RabbitMQ 4.1 mTLS e AMQP 1.0: Guida Pratica per Sviluppatori](docs/blog/configurare_rabbitmq_41_mtls_guida_pratica_dev.md)

## Struttura del Progetto

Consultare la sezione "Struttura del Progetto" nella [guida dettagliata](docs/blog/configurare_rabbitmq_41_mtls_guida_pratica_dev.md).

## Comandi Utili del Makefile

* `make help`: Mostra tutti i target disponibili e le variabili configurabili.
* `make clean`: Rimuove i certificati generati e ferma/rimuove il container RabbitMQ.
* `make rabbitmq-logs`: Mostra i log del container RabbitMQ.

## Licenza

Questo progetto è rilasciato sotto la Licenza MIT. Vedi il file [LICENSE.md](LICENSE.md) per maggiori dettagli.
