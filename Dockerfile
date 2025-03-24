FROM python:3.11-slim as base

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8569

# Create default .env files if they don't exist
RUN touch .env

# Combine .env files from root and chatbot directory and start uvicorn
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8569", "--reload", "--env-file", ".env"]