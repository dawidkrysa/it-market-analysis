# Use a lightweight "slim" image
FROM python:3.13-slim

# Create non-root user with home directory
RUN groupadd -r appuser && useradd -r -g appuser -m -d /home/appuser appuser

# Set the working directory inside the container
WORKDIR /app

# Install system dependencies including Playwright requirements
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    # Delete the temporary list of packages downloaded in step 1
    && rm -rf /var/lib/apt/lists/*

# Copy the requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application code into the container
COPY . .

# Create logs and set ownership
RUN mkdir -p /app/logs && chown -R appuser:appuser /app

# Switch to non-root user BEFORE installing Playwright browsers
USER appuser

# Expose the Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8501/_stcore/health || exit 1

# Start the Streamlit server
CMD ["streamlit", "run", "app.py", "--server.enableCORS", "false"]