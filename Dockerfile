# Use a lightweight "slim" image
FROM python:3.14-slim

# Create non-root user with home directory
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser

# Set the working directory inside the container
WORKDIR /app

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libc6-dev \
    # Delete the temporary list of packages downloaded in step 1
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Create logs
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

# Expose the Streamlit port
EXPOSE 8501

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start the Streamlit server
CMD ["streamlit", "run", "app.py", "--server.enableCORS", "false"]