FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NUMBA_CACHE_DIR=/tmp/numba_cache
ENV PORT=10000
EXPOSE 10000

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

# Attempt to pre-cache the u2netp model; if network hiccups, do not fail the build
RUN python -c "from rembg import new_session; new_session('u2netp')" || true

# Copy project files
COPY . .

# Run the bot
CMD ["python", "main.py"]
