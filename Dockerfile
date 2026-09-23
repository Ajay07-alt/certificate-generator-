FROM python:3.11-slim

WORKDIR /app

# Install system dependencies (fonts, build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    fonts-noto-core \
    fonts-dejavu \
    && rm -rf /var/lib/apt/lists/*

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . .

# Environment variables
ENV PORT=8000
ENV HEADLESS=1

EXPOSE 8000

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8000"]
