FROM python:3.11-slim

# Prevent Python from writing .pyc and buffer stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV U2NET_HOME=/root/.u2net
ENV NUMBA_CACHE_DIR=/tmp/numba_cache

# Install system dependencies required by OpenCV, Pillow, and rembg
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libgomp1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Pre-download the rembg u2netp model into image cache so container starts instantly
RUN python -c "from rembg import new_session; new_session('u2netp')"

# Copy project files
COPY . .

# Run the bot
CMD ["python", "main.py"]
