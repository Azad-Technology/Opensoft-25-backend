# Mindflix: AI-Powered Employee Well-being Platform

## 🎯 Overview

Mindflix transforms traditional employee mood tracking into an intelligent support system that proactively identifies and addresses well-being concerns. Using advanced AI and data analytics, it provides personalized support while generating actionable insights for organizational leadership.

## 🚀 Quick Setup

### Prerequisites

- Python 3.10+
- Neo4j Account (Graph Database)
- MongoDB Atlas Account
- LangSmith Account (API tracing)

### Environment Setup

Create `.env` file from .env.example

### Cloning Steps
```bash
git clone <url>
cd Backend
```


### Installation Options

#### UV (Recommended)
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh  # Installation - https://docs.astral.sh/uv/getting-started/installation/
uv init
uv add -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8569 --reload --env-file .env
```

#### PIP
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app:app --host 0.0.0.0 --port 8569 --reload --env-file .env
```

#### Docker
```bash
docker compose up --build -d
docker compose ps
docker compose logs -f
```

## 📁 Project Structure

```
├── src
│   ├── analysis
│   │   ├── data
│   │   │   ├── activity_tracker_dataset.csv
│   │   │   ├── leave_dataset.csv
│   │   │   ├── onboarding_dataset.csv
│   │   │   ├── performance_dataset.csv
│   │   │   ├── question_bank.py
│   │   │   ├── question_relationships.json
│   │   │   ├── rewards_dataset.csv
│   │   │   ├── tagged_questions.json
│   │   │   └── vibemeter_dataset.csv
│   │   ├── data_analyze_pipeline.py
│   │   └── question_bank_pipeline.py
│   ├── chatbot
│   │   ├── chat_bot.py
│   │   ├── index.py
│   │   ├── llm_models.py
│   │   ├── mentors_system_prompt.py
│   │   ├── mentors.py
│   │   └── system_prompts.py
│   ├── database
│   │   ├── graph_db.py
│   │   └── upload_data.py
│   ├── models
│   │   ├── auth.py
│   │   └── dataset.py
│   ├── routers
│   │   ├── admin.py
│   │   ├── auth.py
│   │   ├── chat.py
│   │   ├── common.py
│   │   └── employee.py
│   └── runner.py
├── utils
│   ├── analysis.py
│   ├── api_key_rotate.py
│   ├── api_logger.py
│   ├── auth.py
│   └── config.py
├── .env
├── .gitignore
├── app.py
├── .devdeploy.sh
├── docker-compose.yml
├── Dockerfile
├── pyproject.toml
├── README.md
├── requirements.txt
├── setup.py
└── uv.lock
```

## 🔄 Core Components

### Data Analysis Pipeline
<p align="center">
  <img src="assets/image (5).png" width="100%" />
</p>

### Chatbot Framework

<p align="center">
  <img src="assets/image (6).png" width="100%" />
</p>

### Mentors

<p align="center">
  <img src="assets/image (7).png" width="100%" />
</p>

## 🔐 Security & Monitoring

### Security Features
- End-to-end encryption
- Role-based access
- API key rotation
- Secure data handling

### Monitoring
- LangSmith API tracing
- Performance metrics
- Error tracking
- Usage analytics

## 🌟 Acknowledgements

- [FastAPI](https://fastapi.tiangolo.com/)
- [Neo4j](https://neo4j.com/)
- [MongoDB](https://www.mongodb.com/)
- [Redis](https://redis.io/)
