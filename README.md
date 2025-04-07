# VibeCatcher: AI-Powered Employee Well-being Platform

<p align="center">
  <img src="assets/vibecatcher_logo.png" alt="VibeCatcher Logo" width="200"/>
</p>

## 🎯 Overview

VibeCatcher transforms traditional employee mood tracking into an intelligent support system that proactively identifies and addresses well-being concerns. Using advanced AI and data analytics, it provides personalized support while generating actionable insights for organizational leadership.

[Insert System Overview Infographic]

## 🏗️ System Architecture

[Insert Technical Architecture Infographic]

## 🚀 Quick Setup

### Prerequisites

- Python 3.10+
- Neo4j Account (Graph Database)
- MongoDB Atlas Account
- LangSmith Account (API tracing)

### Environment Setup

Create `.env` file:

```env
# MongoDB Configuration
MONGODB_URI=mongodb+srv://<username>:<password>@<cluster>.mongodb.net/
MONGODB_NAME=conversational_bot

# Neo4j Configuration
NEO4J_URI=neo4j+s://<id>.databases.neo4j.io
NEO4J_USER=neo4j
NEO4J_PASSWORD=your_password

# LLM API Keys
GROQ_API_KEY1=your_key1
GROQ_API_KEY2=your_key2
GROQ_API_KEY3=your_key3

GOOGLE_API_KEY1=your_key1
GOOGLE_API_KEY2=your_key2
GOOGLE_API_KEY3=your_key3

# Security
ENC_SECRET_KEY=your_secret_key # For password encryption

# LangSmith Tracing
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT="https://api.smith.langchain.com"
LANGSMITH_API_KEY=your_langsmith_key
LANGSMITH_PROJECT=your_project_name
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
[Insert Data Pipeline Infographic]

### Chatbot Framework
[Insert Chatbot Architecture Infographic]


### Post-Chat Analysis
[Insert Analysis System Infographic]


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