# /infra/Dockerfile
# Aligns with PROJECT_BIBLE.md: Section 4
# - 100% containerized, 12-factor, GCP-ready.
# - Docker image is non-root, stateless, and logs to stdout.

# --- Stage 1: Builder ---
# This stage installs dependencies to keep the final image clean.
FROM python:3.11-slim as builder

# Set environment variables to prevent Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create a non-root user
RUN useradd --create-home --shell /bin/bash appuser

WORKDIR /home/appuser

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# --- Stage 2: Final Image ---
# This stage creates the final, lean image for production.
FROM python:3.11-slim

# Set same environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# Create and switch to the non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser
WORKDIR /home/appuser

# Copy installed dependencies from the builder stage
COPY --from=builder /home/appuser/.local /home/appuser/.local
RUN chown -R appuser:appuser /home/appuser

# Copy the application source code
COPY ./src ./src
COPY ./main.py .

# Make sure the app can find the packages
ENV PATH="/home/appuser/.local/bin:${PATH}"

# Define the command to run the application
# This is what gets executed when the container starts.
CMD ["python", "main.py"]
