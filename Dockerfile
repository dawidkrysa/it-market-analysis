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

USER appuser

# Hosting platforms (e.g. Railway) inject the port to listen on via $PORT;
# locally it falls back to 8501.
ENV PORT=8501     PYTHONUNBUFFERED=1     PYTHONDONTWRITEBYTECODE=1
EXPOSE 8501

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3     CMD curl -f "http://localhost:${PORT}/_stcore/health" || exit 1

# Default command: the web app. The scraper job reuses this image with
# "python -m scrapers.run_once" (cron) or "python -m scrapers.scheduler" (compose).
CMD streamlit run app.py     --server.port="${PORT}"     --server.address=0.0.0.0     --server.headless=true     --browser.gatherUsageStats=false
