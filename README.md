# DevPulse

Real-time Developer Activity Intelligence Platform.

Ingests GitHub webhook events, runs ML-based anomaly detection on commit patterns, stores time-series metrics in TimescaleDB, and generates AI-written weekly team health reports via Gemini Pro.


## What it does

- **Webhook ingestion** — receives GitHub push events and streams them into Kafka
- **Anomaly detection** — IsolationForest model flags unusual commit patterns (e.g. 30 commits at 3am)
- **Time-series storage** — TimescaleDB hypertable stores every event with millisecond precision
- **AI digest** — APScheduler triggers Gemini Pro every Monday to write a team health report
- **React dashboard** — dark-theme UI with live Recharts graphs, alert cards, and digest display

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Recharts, inline CSS |
| Backend | FastAPI (Python 3.11) |
| Message queue | Apache Kafka + Zookeeper |
| Time-series DB | TimescaleDB (Postgres extension) |
| Cache | Redis |
| ML | scikit-learn IsolationForest, MLflow |
| AI | Google Gemini Pro API |
| Scheduler | APScheduler |
| CI/CD | GitHub Actions → Docker Hub |
| Containerisation | Docker Compose (6 services) |
| Cloud DB | Neon.tech (TimescaleDB) + Upstash (Redis) |
| Deployment | Railway |

## Architecture

GitHub → FastAPI → Kafka → [DB consumer → TimescaleDB]
→ [ML consumer → Redis alerts]
→ [Log consumer]
APScheduler → Gemini Pro → Redis digest
React → FastAPI → TimescaleDB + Redis

## Quick start

### Prerequisites
- Docker Desktop
- Node 20+
- Python 3.11+

### Run locally

```bash
git clone https://github.com/YOUR_USERNAME/devpulse.git
cd devpulse

cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

docker compose up --build
```

Train the ML model (first time only):
```bash
docker compose exec backend python ml/train.py
```

Open the dashboard: http://localhost:3000

### Send a test webhook

```bash
curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -d '{"pusher":{"name":"alice"},"repository":{"full_name":"org/repo"},"commits":[{},{},{}]}'
```

### Trigger an anomaly

```bash
curl -X POST http://localhost:8000/webhook/github \
  -H "Content-Type: application/json" \
  -d "{\"pusher\":{\"name\":\"mallory\"},\"repository\":{\"full_name\":\"org/repo\"},\"commits\":$(python -c "import json; print(json.dumps([{}]*30))")}"
```

## API endpoints

| Method | Path | Description |
|---|---|---|
| POST | `/webhook/github` | Receive GitHub push events |
| GET | `/api/metrics` | Commits per developer per day (7d) |
| GET | `/api/alerts` | Active anomaly alerts from Redis |
| GET | `/api/digest` | Latest weekly AI digest |
| GET | `/api/health` | Service health check |
| POST | `/api/digest/trigger` | Manually generate digest |

## Running tests

```bash
cd backend
pip install -r requirements.txt
pytest -v
```

## ML model

The IsolationForest is trained on synthetic commit data — normal behaviour (mean=5 commits/day, std=2) plus anomaly samples (26–60 commits). Contamination is set to 0.04. The model is logged to MLflow and saved as `model.pkl`.

View the MLflow experiment UI:
```bash
docker compose exec backend mlflow ui --host 0.0.0.0 --port 5001
# Open http://localhost:5001
```

## Environment variables

| Variable | Description |
|---|---|
| `GEMINI_API_KEY` | Google Gemini Pro API key |
| `REDIS_URL` | Redis connection string |
| `TIMESCALE_URL` | PostgreSQL+asyncpg connection string |
| `KAFKA_BOOTSTRAP` | Kafka broker address |
| `WEBHOOK_SECRET` | GitHub webhook HMAC secret |

## Deployment

Images are pushed to Docker Hub on every merge to `main`. Deploy to Railway manually:

1. Create a new Railway project
2. Add a service from Docker image: `YOUR_USERNAME/devpulse-backend:latest`
3. Set all environment variables (use Neon.tech URL for TimescaleDB, Upstash URL for Redis)
4. Expose port 8000

The frontend can be deployed to Vercel with `REACT_APP_API_URL` pointing to your Railway backend URL.