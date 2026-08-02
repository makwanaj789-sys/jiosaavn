FROM python:3.11-slim

WORKDIR /app

# Environment Variables
ENV API_ID=31812858
ENV API_HASH=037d80c792f88251f405447fe195cc59
ENV BOT_TOKEN=your_new_bot_token_here
ENV DATABASE_URL=sqlite:///jiosaavn.db
ENV PYTHONUNBUFFERED=1

# 🔥 Ye Cookies Set Karo (Netscape Format Wala)

# Install FFmpeg
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "-m", "jiosaavn"]