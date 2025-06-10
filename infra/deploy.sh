#!/bin/bash
# /infra/deploy.sh
# Aligns with PROJECT_BIBLE.md: Section 4, 7
# - Automates the build, push, and deploy process to GCP.

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Configuration ---
# Load variables from the .env file in the project root
if [ ! -f ../.env ]; then
    echo "Error: .env file not found in the project root. Please create it from .env.example."
    exit 1
fi
source ../.env

# Check for required variables
: "${GCP_PROJECT_ID?GCP_PROJECT_ID not set in .env}"
: "${GCP_REGION?GCP_REGION not set in .env}"

IMAGE_REPO="mev-repo" # The name of your Artifact Registry repository
IMAGE_NAME="mev-og-nextgen"
SERVICE_NAME="mev-og-nextgen"
IMAGE_TAG="${GCP_REGION}-docker.pkg.dev/${GCP_PROJECT_ID}/${IMAGE_REPO}/${IMAGE_NAME}:latest"

# --- Deployment Steps ---

echo "--- Enabling GCP Services ---"
gcloud services enable run.googleapis.com \
    artifactregistry.googleapis.com \
    secretmanager.googleapis.com \
    --project=${GCP_PROJECT_ID}

echo "--- Authenticating Docker ---"
gcloud auth configure-docker ${GCP_REGION}-docker.pkg.dev --project=${GCP_PROJECT_ID}

echo "--- Building Docker Image: ${IMAGE_TAG} ---"
docker build -t ${IMAGE_TAG} -f infra/Dockerfile ..

echo "--- Pushing Image to Artifact Registry ---"
docker push ${IMAGE_TAG}

echo "--- Deploying to Cloud Run ---"
# NOTE: The cloudrun.yaml file must be updated with the correct image path!
# This script assumes you have replaced the placeholder.
gcloud run deploy ${SERVICE_NAME} \
    --file=infra/cloudrun.yaml \
    --image=${IMAGE_TAG} \
    --region=${GCP_REGION} \
    --project=${GCP_PROJECT_ID}

echo "--- Deployment Complete ---"
echo "Service URL: $(gcloud run services describe ${SERVICE_NAME} --platform managed --region ${GCP_REGION} --format 'value(status.url)')"
