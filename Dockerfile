FROM python:3.11-slim

WORKDIR /app

# Directly Keys Set करें
ENV API_ID=31812858
ENV API_HASH=037d80c792f88251f405447fe195cc59
ENV BOT_TOKEN=your_new_bot_token_here
ENV DATABASE_URL=sqlite:///jiosaavn.db

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python3", "-m", "jiosaavn"]