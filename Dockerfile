FROM python:3.11-slim

# Established the working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create necessary directories and add non-root user
RUN mkdir -p uploads audio logs \
    && useradd -u 1000 -m appuser \
    && chown -R appuser:appuser /app

USER appuser

# Expose port
EXPOSE 8000

# Default environment variables
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO

# Run uvicorn directly; migrations are handled outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]