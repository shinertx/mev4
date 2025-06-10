# MEV-OG NextGen — Institutional-Grade MEV Engine

This repository contains the source code for MEV-OG NextGen, a modular, AI-native, and adversarially-resilient crypto trading engine. The system is designed to autonomously compound capital via MEV, arbitrage, and liquidation opportunities across a wide range of on-chain and off-chain venues.

The architecture and operation of this system are strictly governed by the principles laid out in the `PROJECT_BIBLE.md`.

---

## 1. System Vision & Core Principles

The system is designed from the ground up to be institutional-grade, with a non-negotiable emphasis on safety, auditability, and resilience.

- **Atomicity & State Isolation:** All trade and session state is atomic, isolated, and rollbackable. There is no global state.
- **System-Wide Kill Switch:** A non-bypassable kill switch can halt all system operations instantly. Every capital-moving component must check its status before execution.
- **Simulation First:** No strategy is deployed to mainnet without passing a rigorous suite of tests in forked and simulated environments.
- **100% Containerized & GCP-Ready:** The system is designed for 12-factor, stateless deployment on Google Cloud Run, ensuring scalability and operational consistency.
- **Comprehensive Auditability:** Every action, state change, error, and configuration change is logged in a structured format for real-time monitoring and post-mortem analysis.

---

## 2. Project Structure

/src/ # Main application source code
/core/ # Core system components (agent, state, tx, kill, DRP)
/adapters/ # Modular adapters for external venues (DEX, CEX, Bridge)
/strategies/ # Implementations of trading/MEV strategies
/test/ # All unit, integration, and simulation tests
/infra/ # Docker, Docker Compose, and GCP deployment assets
/scripts/ # Supporting shell scripts for setup and ops
.env.example # Template for environment variables and secrets
requirements.txt # Python package dependencies
main.py # Main application entrypoint
PROJECT_BIBLE.md # The constitutional source of truth for the system
README.md # This file


---

## 3. Setup and Local Onboarding

Follow these steps to set up the project for local development and testing.

### Prerequisites
- [Git](https://git-scm.com/)
- [Python 3.11+](https://www.python.org/)
- [Docker](https://www.docker.com/) & [Docker Compose](https://docs.docker.com/compose/)

### Step-by-Step Instructions

1.  **Clone the Repository:**
    ```bash
    git clone <your-repo-url>
    cd <your-repo-name>
    ```

2.  **Create your Environment File:**
    Copy the example environment file and fill in your details.
    ```bash
    cp .env.example .env
    ```
    Now, open `.env` in an editor and add your `EXECUTOR_PRIVATE_KEY`, `ETH_RPC_URL`, and any other required API keys.

3.  **Install Python Dependencies:**
    It is highly recommended to use a Python virtual environment.
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    pip install --no-cache-dir --upgrade pip
    pip install --no-cache-dir -r requirements.txt
    ```

---

## 4. Running the System

### Running Locally with Docker Compose
For standard local development, use Docker Compose. This ensures the application runs in a containerized environment identical to production.

From the `infra/` directory, run:
```bash
# Navigate to the infra directory
cd infra/

# Build and start the service in the foreground
docker-compose up --build
The application will start, and you will see structured logs in your terminal. To stop the application, press Ctrl+C.

Running Tests
The system uses pytest for all testing. Tests are located in the /test directory and utilize mock adapters to ensure isolated and predictable results.

From the project root directory, run:

pytest
This command will automatically discover and run all tests. Ensure all tests are passing before committing code.

5. Deployment to GCP Cloud Run
The system is designed for declarative, one-command deployment to GCP Cloud Run.

Prerequisites
gcloud CLI: Install and initialize the Google Cloud CLI.
GCP Project: Have a GCP project with the Project ID and Region configured in your .env file.
Enable APIs: Ensure Artifact Registry, Cloud Run, and Secret Manager APIs are enabled for your project.
Create Production Secrets: Store your EXECUTOR_PRIVATE_KEY, ETH_RPC_URL, etc., in GCP Secret Manager. The names must match the keys in infra/cloudrun.yaml.
Deployment Command
The deploy.sh script automates the entire process of building the image, pushing it to Artifact Registry, and deploying the service to Cloud Run.

From the infra/ directory, run:

# Make sure the script is executable
chmod +x deploy.sh

# Run the deployment script
./deploy.sh
The script will guide you through the process and output the service URL upon completion.

6. Troubleshooting
Container Fails to Start: Check the container logs with docker logs mev-og-nextgen. The most common cause is a missing or invalid variable in your .env file.
Authentication Errors (GCP): Ensure you have run gcloud auth login and gcloud auth configure-docker.
Transaction Fails: Check the logs for TRANSACTION_VALIDATION_ERROR or TRANSACTION_SEND_FAILURE. This often indicates issues with gas, nonce, or network connectivity.

---

### **PROJECT BLUEPRINT COMPLETE**

All components specified in the `PROJECT_BIBLE.md`—from core logic and safety systems to a full suite of strategies, adapters, tests, and deployment infrastructure—have been created. The foundational architecture is now complete and validated.

The system is ready for the next phase: continuous expansion with new strategies, integration with more venues, and rigorous, adversarial testing in live simulation environments.

I am ready for your next directive.
