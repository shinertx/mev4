#!/bin/bash
set -e

gcloud builds submit --tag gcr.io/your-project/mev:latest ..
gcloud run deploy mev-service --image gcr.io/your-project/mev:latest --platform managed
