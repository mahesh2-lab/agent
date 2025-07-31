# syntax=docker/dockerfile:1

# ---- Builder Stage ----
# This stage installs dependencies and compiles assets.
ARG PYTHON_VERSION=3.11.6
FROM python:${PYTHON_VERSION}-slim AS builder

# Set working directory
WORKDIR /app

# Install system-level build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only the requirements file to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN python -m pip install --no-cache-dir -r requirements.txt


# ---- Final Stage ----
# This stage creates the lean, production-ready image.
FROM python:${PYTHON_VERSION}-slim

# Keeps Python from buffering stdout and stderr
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

# Set the user
USER appuser
WORKDIR /home/appuser

# Copy installed Python packages from the builder stage
COPY --from=builder /usr/local /usr/local

# Add packages to PATH
ENV PATH=/home/appuser/.local/bin:$PATH

# Copy the application source code
COPY . .

# Download any dependent models at build-time
RUN python main.py download-files

# Expose the healthcheck port
EXPOSE 8081

# Set the default command to run the application
CMD ["python", "main.py", "start"]