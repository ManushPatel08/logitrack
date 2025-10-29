# 🚢 LogiTrack AI: The Proactive Shipment Analyzer

An intelligent, real-time shipment tracking and analytics platform. This full-stack application ingests and analyzes global shipment data, providing instant delay detection, predictive insights, and a live tracking dashboard.

---

## 🎯 Key Features

- **Real-Time Analytics:** A "Mission Control" dashboard with live KPIs for active, at-risk, and on-track shipments.  
- **Interactive Global Map:** Visualizes the most recent location of active shipments, color-coded by status.  
- **AI-Powered Classification:** (Real Mode) Uses a Hugging Face model (BART-MNLI) for zero-shot classification of raw status text to determine shipment status and delay reasons.  
- **Delay Analysis:** Dynamically generated charts showing breakdowns of delay reasons (Weather, Customs, Port Congestion, etc.).  
- **At-Risk Alerts:** A table isolating shipments classified as **Delayed** for immediate attention.  
- **Dockerized Services:** PostgreSQL, FastAPI backend, Streamlit frontend, and a Python worker orchestrated with Docker Compose.

---

## 🏗️ Architecture (High Level)

Streamlit UI (frontend, :8501) <--HTTP--> FastAPI Backend (:8000) <--SQL--> PostgreSQL (db)
^
|
Worker (AI / ingest)
|
(Hugging Face API - optional)

yaml
Copy code

---

## 🛠️ Tech Stack

- **Backend:** FastAPI (Python), SQLModel  
- **Frontend:** Streamlit, Plotly, Pandas  
- **Database:** PostgreSQL  
- **AI/ML:** Hugging Face Transformers (optional, Real Mode)  
- **Infrastructure:** Docker & Docker Compose

---

## 📁 Project Structure

LogiTrackProject/
├── backend/
│ ├── main.py # FastAPI app & endpoints
│ ├── models.py # Database models (SQLModel)
│ ├── database.py # Database connection logic
│ ├── requirements.txt
│ └── Dockerfile
├── frontend/
│ ├── app.py # Streamlit dashboard code
│ ├── requirements.txt
│ └── Dockerfile
├── worker/
│ ├── worker.py # Data ingestion worker (real or mock)
│ ├── seed_database.py # Script to pre-load mock data
│ ├── mock_data.py # Pre-processed mock events
│ ├── requirements.txt
│ └── Dockerfile
├── docker-compose.yml # Orchestrates all services
├── setup.sql # Database schema
├── .env.example # Example environment file (placeholders)
├── .gitignore
├── generate_mock_data.py # Utility to create mock_data.py
└── README.md

yaml
Copy code

---

## 🚀 Quick Start

<<<<<<< HEAD
### 1. Prerequisites
=======
bashgit clone https://github.com/ManushPatel08/logitrack.git
cd logitrack-ai
>>>>>>> 2ef0eecaf108621d0617e16498bad760ad542315

- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Git](https://git-scm.com/)

### 2. Clone & Setup Environment

```bash
# Clone the repository
git clone https://github.com/ManushPatel08/logitrack.git
cd logitrack

# Copy the example env file
cp .env.example .env   # or use: copy .env.example .env (Windows)
IMPORTANT: Do not commit your local .env to version control. It’s already listed in .gitignore.

Open .env and replace the placeholders with your own secrets.

3. Build & Start All Services
bash
Copy code
docker-compose up --build -d
4. Initialize the Database Schema
Run once to create tables.

macOS / Linux:

bash
Copy code
docker exec -i logitrack_db psql -U <POSTGRES_USER> -d <POSTGRES_DB> < setup.sql
Windows PowerShell:

powershell
Copy code
Get-Content setup.sql | docker exec -i logitrack_db psql -U <POSTGRES_USER> -d <POSTGRES_DB>

5. Seed the Database with Mock Data
bash
Copy code
docker-compose run --rm worker python seed_database.py
This clears any existing data and populates the database with mock events.

6. Access the Application
Frontend Dashboard: http://localhost:8501

API Docs (FastAPI): http://localhost:8000/docs

Database (local access): localhost:5433 (User: from .env)

The worker service will continue inserting a new random event every ~30 seconds.

🤖 Data & AI Modes
Controlled by USE_REAL_API in your .env:

USE_REAL_API=false (default):

Runs in Mock Mode using preloaded data (no external API calls).

USE_REAL_API=true:

Runs in Real Mode using live data sources and Hugging Face API for classification.

Requires a valid Hugging Face API key in .env.

📦 Re-generate Mock Data
bash
Copy code
# Generate new mock_data.py
python generate_mock_data.py > worker/mock_data.py

# Rebuild the worker image
docker-compose build worker

# Re-seed database
docker-compose run --rm worker python seed_database.py
🧪 Testing & Logs
bash
Copy code
# Test backend API health
curl http://localhost:8000/health

# View logs for any service
docker-compose logs -f worker
🔧 Environment Variables (.env.example)
Never commit your .env file. Use this template instead:

env
Copy code
# ===== Database =====
POSTGRES_USER=<POSTGRES_USER_PLACEHOLDER>
POSTGRES_PASSWORD=<POSTGRES_PASSWORD_PLACEHOLDER>
POSTGRES_DB=<POSTGRES_DB_PLACEHOLDER>
POSTGRES_HOST=db

# ===== API & AI =====
HF_API_KEY=<HUGGING_FACE_API_KEY_PLACEHOLDER>     # Required if USE_REAL_API=true
API_URL=http://backend:8000

# ===== Modes & 3rd-party =====
USE_REAL_API=false
USE_MARINETRAFFIC_API=false
MARINETRAFFIC_API_KEY=<MARINETRAFFIC_API_KEY_PLACEHOLDER>

# ===== Ports (optional) =====
# FRONTEND_PORT=8501
# BACKEND_PORT=8000
# POSTGRES_PORT=5433
🔐 Security Best Practices
Never commit real credentials or .env files to Git.

Use Docker secrets, Vault, or CI/CD secret stores for production.

Use least-privilege DB users and rotate passwords/API keys regularly.

Avoid exposing DB ports publicly unless necessary.

👨‍💻 Author
Manush Patel
GitHub: ManushPatel08
LinkedIn: linkedin.com/in/manush-patel08

🙏 Acknowledgments
Hugging Face (BART-MNLI model)

FastAPI

Streamlit

PostgreSQL