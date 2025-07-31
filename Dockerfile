# syntax=docker/dockerfile:1

# ---- Builder Stage ----
# This stage installs dependencies using build tools.
ARG PYTHON_VERSION=3.11.6
FROM python:${PYTHON_VERSION}-slim AS builder

WORKDIR /app

# Install system-level build dependencies like gcc
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file to leverage Docker's build cache
COPY requirements.txt .

# Install Python dependencies to the user directory
RUN python -m pip install \
    --no-cache-dir \
    --user \
    --no-warn-script-location \
    -r requirements.txt


# ---- Final Stage ----
# This stage creates the lean, production-ready image.
FROM python:${PYTHON_VERSION}-slim

# Set environment variable to prevent output buffering
ENV PYTHONUNBUFFERED=1

# Create a non-privileged user for security
ARG UID=10001
RUN adduser \
    --disabled-password \
    --gecos "" \
    --home "/home/appuser" \
    --shell "/sbin/nologin" \
    --uid "${UID}" \
    appuser

# Switch to the new user
USER appuser
WORKDIR /home/appuser

# Copy installed Python packages from the builder stage
COPY --from=builder /root/.local /home/appuser/.local

# Add the user's local bin to the PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy the application source code
COPY . .

# Download any dependent models at build-time
RUN python main.py download-files

# FIX: Manually create the directory for transcripts
RUN mkdir -p ./tmp

# Expose the application's port
EXPOSE 8081

# Set the default command to run the application
CMD ["python", "main.py", "start"]