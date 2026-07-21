FROM python:3.11-slim

# Install curl for Docker healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Create a non-root user for security
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Install Python dependencies (cached layer)
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy only backend runtime code. The frontend has its own image.
COPY --chown=user main.py ./
COPY --chown=user services ./services
COPY --chown=user data ./data

# Create required directories for persistent data
RUN mkdir -p vectorstore data

# Expose FastAPI port
EXPOSE 9999

# Run with single worker (FAISS is not thread-safe with multiple workers)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9999", "--workers", "1"]
