FROM python:3.11-slim

ENV JAVA_HOME=/usr/lib/jvm/java-11-openjdk-amd64
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Install system dependencies
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       gcc \
       g++ \
       git \
       unzip \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy the rest of the project files (excluding data initially)
COPY . .

# Copy data explicitly to ensure it's included
COPY data/raw/MachineLearningCSV/MachineLearningCVE/*.csv /app/data/raw/MachineLearningCSV/MachineLearningCVE/

# Verify CSV files are present
RUN ls -la /app/data/raw/MachineLearningCSV/MachineLearningCVE/ && echo "CSV files found!"

# Create checkpoint directory
RUN mkdir -p /app/checkpoints

# Default command
CMD ["python", "experiments/main_experiment.py"]
