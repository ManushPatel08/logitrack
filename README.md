🚢 LogiTrack AI: The Proactive Shipment Analyzer

An intelligent, real-time shipment tracking and analytics platform powered by AI, providing instant delay detection, predictive insights, and live global tracking.

🎯 Project Overview
LogiTrack AI is a full-stack logistics intelligence platform that automatically:

📊 Ingests raw shipment status data from multiple sources
🤖 Processes and classifies events using AI (Hugging Face BART-MNLI)
📈 Provides real-time analytics and KPI dashboards
🗺️ Tracks shipments globally with interactive maps
⚠️ Identifies at-risk shipments proactively

🏗️ Architecture
┌─────────────────┐
│   Streamlit UI  │  ← User Interface (Port 8501)
│   (Frontend)    │
└────────┬────────┘
         │ HTTP
         ▼
┌─────────────────┐
│   FastAPI       │  ← REST API (Port 8000)
│   (Backend)     │
└────────┬────────┘
         │ SQL
         ▼
┌─────────────────┐     ┌──────────────┐
│   PostgreSQL    │◄────┤ Worker (AI)  │
│   (Database)    │     │ + Data Ingest│
└─────────────────┘     └──────────────┘
                              │
                              ▼
                        Hugging Face API
🛠️ Tech Stack
Backend:

FastAPI (Python web framework)
SQLModel (ORM)
PostgreSQL (Database)

Frontend:

Streamlit (Dashboard UI)
Plotly (Interactive charts & maps)
Pandas (Data processing)

AI/ML:

Hugging Face Transformers (BART-MNLI)
Zero-shot text classification

Infrastructure:

Docker & Docker Compose
Python 3.10

📁 Project Structure
LogiTrackProject/
├── backend/
│   ├── main.py              # FastAPI app & endpoints
│   ├── models.py            # Database models
│   ├── database.py          # DB connection
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── app.py               # Streamlit dashboard
│   ├── requirements.txt
│   └── Dockerfile
├── worker/
│   ├── worker.py            # Data ingestion + AI processing
│   ├── requirements.txt
│   └── Dockerfile
├── docker-compose.yml       # Orchestration
├── setup.sql                # Database schema
├── .env                     # Environment variables
└── README.md
🚀 Quick Start
Prerequisites

Docker Desktop installed
Git
8GB RAM minimum

Installation

Clone the repository

bashgit clone https://github.com/ManushPatel08/logitrack.git
cd logitrack-ai

Create .env file

bash# Copy the example
cp .env.example .env

# Edit with your API keys
nano .env

Start the application

bash# Build and start all services
docker-compose up --build

# Or run in detached mode
docker-compose up -d

Initialize the database (first time only)

bashdocker exec -i logitrack_db psql -U admin -d logitrack < setup.sql

Access the dashboard


Frontend UI: http://localhost:8501
API Documentation: http://localhost:8000/docs
Database: localhost:5433

📊 Features
1. Real-Time Analytics Dashboard

Total active shipments
Delay percentage and count
On-time delivery metrics
Total delay incidents

2. Interactive Global Map

Live shipment locations worldwide
Color-coded status indicators
Hover tooltips with detailed info
Filter by status or tracking ID

3. Delay Analysis

Bar chart of delay reasons
Breakdown by: Weather, Customs, Port Congestion
Historical trend tracking

4. Status Distribution

Pie chart visualization
Categories: On Time, Delayed, Delivered
Percentage calculations

5. At-Risk Shipment Alerts

Real-time identification
Tracking ID, origin, destination
Sortable and filterable table

🔌 API Endpoints
Health Check
GET /health
GET /health/db
Analytics
GET /api/v1/kpi/delay_reasons
Response: [{"ai_reason": "Weather Delay", "count": 5}, ...]
Shipments
GET /api/v1/shipments/at_risk
Response: [{"id": 1, "tracking_id": "TRK123", ...}, ...]

GET /api/v1/shipments/live_locations
Response: [{"tracking_id": "TRK123", "lat": 40.7, "lon": -74.0, ...}, ...]
🤖 AI Processing
The worker service uses zero-shot classification with BART-MNLI to categorize raw status text:
Input: "Vessel delayed at port due to congestion"
Output:

Status: Delayed
Reason: Port Congestion

Categories:

On Time
Delayed (Weather Delay, Customs Issue, Port Congestion)
Delivered

🗄️ Database Schema
sqlshipments
- id (PK)
- tracking_id (unique)
- origin
- destination
- created_at

shipment_events
- id (PK)
- shipment_id (FK)
- timestamp
- location
- raw_status_text
- ai_status (AI-generated)
- ai_reason (AI-generated)
- latitude
- longitude
🔧 Configuration
Environment Variables
VariableDescriptionDefaultPOSTGRES_USERDatabase usernameadminPOSTGRES_PASSWORDDatabase passwordsecretPOSTGRES_DBDatabase namelogitrackPOSTGRES_HOSTDatabase hostdbHF_API_KEYHugging Face API keyRequiredAPI_URLBackend API URLhttp://backend:8000
📈 Development Roadmap

 Database schema design
 Data ingestion worker
 AI classification pipeline
 REST API endpoints
 Interactive dashboard
 Global map visualization
 User authentication
 Email alerts for delays
 Predictive ETA calculations
 Multi-carrier integration
 Mobile app

🧪 Testing
bash# Test backend API
curl http://localhost:8000/health

# Test database connection
docker exec -it logitrack_db psql -U admin -d logitrack -c "SELECT COUNT(*) FROM shipments;"

# View worker logs
docker logs logitrack-worker-1
🐛 Troubleshooting
Worker not processing data?
bash# Check worker logs
docker logs logitrack-worker-1 -f

# Restart worker
docker-compose restart worker
Database connection failed?
bash# Check if DB is running
docker ps | grep postgres

# Access database directly
docker exec -it logitrack_db psql -U admin -d logitrack
Frontend not loading?
bash# Check frontend logs
docker logs logitrack-frontend-1

# Rebuild frontend
docker-compose up --build frontend
📝 License
MIT License - see LICENSE file for details
👨‍💻 Author
Your Name

GitHub: ManushPatel08
LinkedIn: www.linkedin.com/in/manush-patel08

🙏 Acknowledgments

Hugging Face for the BART-MNLI model
FastAPI framework
Streamlit community
PostgreSQL team


🌟 Support
⭐ Star this repo if you find it useful!
📧 Questions? Open an issue or contact me directly.
