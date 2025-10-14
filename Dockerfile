FROM python:3.14-slim

# Docker Image Labels
LABEL org.opencontainers.image.title="Realtime API"
LABEL org.opencontainers.image.description="Production-ready Realtime API with Asterisk ARI integration"
LABEL org.opencontainers.image.vendor="Realtime API"
LABEL org.opencontainers.image.url="https://github.com/dny1020/realtime-session-api"
LABEL org.opencontainers.image.source="https://github.com/dny1020/realtime-session-api"
LABEL org.opencontainers.image.documentation="https://github.com/dny1020/realtime-session-api/blob/main/README.md"
LABEL org.opencontainers.image.licenses="MIT"

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

# Health check
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run uvicorn directly; migrations are handled outside the container
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]