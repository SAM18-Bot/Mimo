FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    portaudio19-dev \
    libgl1 \
    libglib2.0-0 \
    espeak \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN sed -i '/pygetwindow/d' requirements.txt && \
    sed -i '/pywebview/d' requirements.txt && \
    sed -i '/pystray/d' requirements.txt && \
    sed -i '/plyer/d' requirements.txt && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Set environment variables for headless cloud run
ENV NO_HARDWARE=1
ENV NO_VOICE=1
ENV NO_TRACKER=1
ENV PYTHONUNBUFFERED=1

# Command to run the FastAPI app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
