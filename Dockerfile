FROM python:3.10-slim

WORKDIR /app

# Copy the project files
COPY . .

# Install the package in development mode
RUN pip install --no-cache-dir -e .

# Expose the port
EXPOSE 9000

# Set environment variables
ENV HOST=0.0.0.0
ENV PORT=9000

# Command to run the server
CMD ["python", "server.py", "--host", "0.0.0.0", "--port", "9000", "--server-url", "${MCP_SERVER_URL}"]