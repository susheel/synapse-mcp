FROM python:3.10-slim

WORKDIR /app

# Install system dependencies for cryptographic libraries
RUN apt-get update && apt-get install -y \
    build-essential \
    libffi-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy the project files
COPY . .

# Install the package in development mode
RUN pip install --no-cache-dir -e .

# Expose the port
EXPOSE 9000

# Set environment variables
ENV HOST="0.0.0.0"
ENV PORT="9000"

# Command to run the server
CMD ["python", "-m", "synapse_mcp", "--debug"]