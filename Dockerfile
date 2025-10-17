FROM ubuntu:22.04

# System setup
RUN apt-get update && apt-get install -y \
    python3.13 python3.13-venv python3-pip \
    git build-essential curl wget \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy project files
COPY . /app

# Python venv and dependencies
RUN python3.13 -m venv .venv && \
    . .venv/bin/activate && \
    pip install --upgrade pip && \
    pip install -r requirements.txt

# Entrypoint for bash shell
ENTRYPOINT ["/bin/bash"]
