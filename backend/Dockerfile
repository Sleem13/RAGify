FROM python:3.11

WORKDIR /app

# Create a non-root user
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH

WORKDIR $HOME/app

# Copy requirements and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY --chown=user . .

# Expose port 9999
EXPOSE 9999

# Run FastAPI using uvicorn on port 9999
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "9999"]
