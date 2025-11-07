# 🚢 LogiTrack AI - Real-Time Maritime Shipment Intelligence

[![Live Demo](https://img.shields.io/badge/Demo-Live-success?style=for-the-badge)](https://logitrack-frontend.streamlit.app)
[![Backend API](https://img.shields.io/badge/API-Live-blue?style=for-the-badge)](https://logitrack-shiptrack-backend.onrender.com)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black?style=for-the-badge&logo=github)](https://github.com/ManushPatel08/logitrack)

An intelligent, real-time shipment tracking and analytics platform that monitors global maritime traffic using **AIS (Automatic Identification System)** data. Track ships worldwide, analyze delays, and get AI-powered insights - all in real-time!

---

## 🌐 Live Demo & Links

**🎯 Frontend Dashboard**: [https://logitrack-frontend.streamlit.app](https://logitrack-frontend.streamlit.app)

**🔗 Backend API**: [https://logitrack-shiptrack-backend.onrender.com](https://logitrack-shiptrack-backend.onrender.com)

**📊 API Health Check**: [https://logitrack-shiptrack-backend.onrender.com/health](https://logitrack-shiptrack-backend.onrender.com/health)

**📚 API Documentation**: [https://logitrack-shiptrack-backend.onrender.com/docs](https://logitrack-shiptrack-backend.onrender.com/docs)

**💾 Database Health**: [https://logitrack-shiptrack-backend.onrender.com/health/db](https://logitrack-shiptrack-backend.onrender.com/health/db)

---

## ✨ Key Features

### 📊 Real-Time Analytics Dashboard
- **Mission Control KPIs**: Active shipments, at-risk vessels, on-track deliveries, and total delay incidents
- **Live Updates**: Auto-refreshes every 15 seconds
- **System Health Monitoring**: Real-time API, database, and worker status indicators

### 🗺️ Interactive Global Map
- **Live Ship Tracking**: Visualize real ships from AIS stream data
- **Color-Coded Status**: Green (On Time), Red (Delayed), Blue (Delivered)
- **Geographic Filters**: Filter by status, tracking ID, or bounding box
- **Hover Details**: View ship name, location, coordinates, and timestamp

### 🤖 AI-Powered Classification
- **Intelligent Status Detection**: AI categorizes ship navigational status
- **Delay Reason Analysis**: Automatically identifies port congestion, weather delays, customs issues
- **Text Paraphrasing**: Human-friendly status descriptions using Hugging Face API
- **Stationary Detection**: Flags ships stuck at anchor for extended periods

### 📈 Advanced Analytics
- **Delay Breakdown Charts**: Bar charts showing reasons for delays
- **Status Distribution**: Pie charts visualizing shipment status proportions
- **At-Risk Alerts**: Priority table highlighting delayed shipments
- **Trend Analysis**: Historical data for performance insights

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         FRONTEND                                │
│              Streamlit Dashboard (Port 8501)                    │
│         https://logitrack-frontend.streamlit.app                │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/REST API
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    BACKEND API + WORKER                         │
│                  FastAPI (Port 10000)                           │
│      https://logitrack-shiptrack-backend.onrender.com           │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │        Integrated Background Worker Thread               │  │
│  │  • Runs inside FastAPI on startup                        │  │
│  │  • AIS Stream WebSocket Connection                       │  │
│  │  • Data Ingestion & Processing (60s cycles)              │  │
│  │  • AI Classification (Hugging Face FLAN-T5)              │  │
│  │  • Heuristic Fallback Logic                              │  │
│  └──────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │ SQL (psycopg2)
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                   POSTGRESQL DATABASE                           │
│                  Neon (Serverless)                              │
│                                                                 │
│  Tables: shipments, shipment_events                             │
│  Indexes: tracking_id, ai_status, coordinates                  │
└─────────────────────────────────────────────────────────────────┘
                         ▲
                         │ WebSocket (wss://)
                         │
┌─────────────────────────────────────────────────────────────────┐
│                    AIS STREAM API                               │
│              Real-time Ship Position Data                       │
│               https://aisstream.io                              │
└─────────────────────────────────────────────────────────────────┘
```

### Key Architecture Notes:
- **Worker is integrated into Backend**: The worker runs as a background thread inside the FastAPI application, not as a separate service
- **Single Deployment**: Backend + Worker deployed together on Render as one service
- **background_worker.py**: Starts the worker thread on FastAPI startup
- **Worker files copied to backend/**: `worker.py` and `mock_data.py` exist in both `backend/` and `worker/` directories

---

## 🛠️ Tech Stack

### Backend
- **FastAPI** - High-performance async API framework
- **SQLModel** - SQL database ORM with Pydantic validation
- **PostgreSQL** - Robust relational database (Neon serverless)
- **psycopg2** - PostgreSQL adapter for Python
- **Threading** - Background worker integration

### Frontend
- **Streamlit** - Interactive web dashboard
- **Plotly** - Interactive charts and maps
- **Pandas** - Data manipulation and analysis (>=2.2.0 for Python 3.13)

### AI/ML
- **Hugging Face Transformers** - AI text processing (FLAN-T5)
- **Custom Heuristics** - Fallback classification logic for speed

### Infrastructure
- **Docker** - Containerization for local development
- **Render** - Backend hosting (free tier with auto-sleep)
- **Streamlit Cloud** - Frontend hosting (free tier)
- **Neon** - PostgreSQL hosting (serverless free tier)

### External APIs
- **AISStream.io** - Real-time maritime AIS data (WebSocket)
- **Hugging Face API** - AI model inference

---

## 📁 Project Structure

```
LogiTrackProject/
├── backend/
│   ├── main.py                 # FastAPI app with startup event
│   ├── database.py             # Database connection (prioritizes DATABASE_URL)
│   ├── models.py               # SQLModel database models
│   ├── background_worker.py    # Worker thread integration
│   ├── worker.py               # Worker logic (copied from worker/)
│   ├── mock_data.py            # Mock shipment data (copied from worker/)
│   ├── requirements.txt        # Backend + worker dependencies
│   └── Dockerfile              # Backend container config
│
├── frontend/
│   ├── app.py                  # Streamlit dashboard application
│   ├── requirements.txt        # Frontend dependencies (pandas>=2.2.0)
│   └── Dockerfile              # Frontend container config
│
├── worker/                     # Original worker files (for local Docker)
│   ├── worker.py               # Standalone worker (Docker Compose only)
│   ├── mock_data.py            # Pre-generated mock events
│   ├── seed_database.py        # Database seeding script
│   ├── requirements.txt        # Worker dependencies
│   └── Dockerfile              # Worker container config
│
├── docker-compose.yml          # Local development orchestration
├── setup.sql                   # Database schema initialization
├── render.yaml                 # Render deployment config
├── .env                        # Environment variables (not in repo)
├── .gitignore                  # Git ignore rules
└── README.md                   # This file
```

### Why Two Worker Locations?
- **`backend/worker.py`**: Used in cloud deployment (Render) - worker runs inside FastAPI
- **`worker/worker.py`**: Used in local Docker Compose - worker runs as separate container
- Files are synced manually when changes are made

---

## 🚀 Cloud Deployment (FREE)

The application is deployed using **100% free tiers**:

### 1. **Neon PostgreSQL** (Database)
- ✅ Serverless PostgreSQL with auto-scaling
- ✅ Free tier: 0.5 GB storage, 1 project
- ✅ Connection pooling and SSL
- 🔗 [https://neon.tech](https://neon.tech)

### 2. **Render** (Backend + Integrated Worker)
- ✅ Backend API with integrated worker thread
- ✅ Free tier with auto-sleep after 15 min inactivity
- ✅ Auto-deploy from GitHub
- ⚠️ First request takes 30-60s to wake up
- 🔗 [https://render.com](https://render.com)

### 3. **Streamlit Cloud** (Frontend)
- ✅ Interactive dashboard with auto-deploy
- ✅ Free public app hosting
- ✅ Direct GitHub integration
- 🔗 [https://share.streamlit.io](https://share.streamlit.io)

### 4. **AISStream** (Real-time Ship Data)
- ✅ WebSocket API for live AIS data
- ✅ Free tier available (limited requests)
- 🔗 [https://aisstream.io](https://aisstream.io)

**💰 Total Cost: $0/month** 🎉

---

## 🏠 Local Development

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- [Git](https://git-scm.com/)

### Quick Start

```bash
# Clone repository
git clone https://github.com/ManushPatel08/logitrack.git
cd logitrack

# Create environment file
copy .env.example .env  # Windows
# OR
cp .env.example .env    # macOS/Linux

# Edit .env with your credentials

# Start all services
docker-compose up --build

# Initialize database (first time only)
docker exec -i logitrack_db psql -U admin -d logitrack < setup.sql

# Access the application
# Frontend: http://localhost:8501
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/docs
```

---

## ⚙️ Configuration

### Environment Variables

Create a `.env` file with these variables:

```bash
# ===== Database =====
DATABASE_URL=postgresql://user:pass@host/db  # Neon connection string (PRIORITY)
POSTGRES_USER=admin                          # Fallback for local Docker
POSTGRES_PASSWORD=your_password              # Fallback for local Docker
POSTGRES_DB=logitrack                        # Fallback for local Docker
POSTGRES_HOST=db                             # Docker service name

# ===== API Keys =====
HF_API_KEY=your_huggingface_api_key          # Hugging Face for AI
AISSTREAM_WS_API_KEY=your_aisstream_key      # AISStream WebSocket

# ===== Data Source =====
USE_AIS_API=true                             # true = real ships, false = mock data
DISABLE_MOCK_INGEST=true                     # true = AIS only, false = include mock
ENABLE_BACKGROUND_WORKER=true                # Enable integrated worker

# ===== AIS Configuration =====
AISSTREAM_MODE=ws                            # WebSocket mode
AISSTREAM_WS_URL=wss://stream.aisstream.io/v0/stream
AISSTREAM_WS_BOUNDING_BOXES=[[[1.0,103.5],[1.5,104.5]]]  # Singapore
AISSTREAM_WS_RECEIVE_WINDOW_SECS=120        # Message timeout
AISSTREAM_WS_SUBSCRIBE_TIMEOUT_SECS=10      # Subscribe timeout

# ===== Backend =====
API_URL=http://backend:8000                  # For Docker networking

# ===== AI Processing =====
AI_MAX_PER_CYCLE=3                           # Max AI calls per cycle
AI_FALLBACK_HEURISTICS=true                  # Use heuristics if AI fails
```

### Geographic Bounding Boxes

Choose busy shipping areas for faster results:

```bash
# Singapore Strait (busiest - recommended)
AISSTREAM_WS_BOUNDING_BOXES=[[[1.0,103.5],[1.5,104.5]]]

# English Channel
AISSTREAM_WS_BOUNDING_BOXES=[[[49.5,-5.0],[51.0,2.0]]]

# Panama Canal
AISSTREAM_WS_BOUNDING_BOXES=[[[8.5,-80.0],[9.5,-79.0]]]

# Global (slower, not recommended)
AISSTREAM_WS_BOUNDING_BOXES=[[[-90,-180],[90,180]]]
```

---

## 🔌 API Endpoints

### Health & Status
- `GET /health` - API health status
- `GET /health/db` - Database connection status

### KPIs & Analytics
- `GET /api/v1/kpi/delay_reasons` - Delay reasons with counts
- `GET /api/v1/shipments/at_risk` - List of delayed shipments

### Shipment Data
- `GET /api/v1/shipments/live_locations?limit=1000` - Live ship locations with coordinates

### Documentation
- `GET /docs` - Interactive API documentation (Swagger UI)
- `GET /redoc` - Alternative API documentation (ReDoc)

---

## 📊 Database Schema

```sql
-- Shipments table
CREATE TABLE shipments (
    id SERIAL PRIMARY KEY,
    tracking_id VARCHAR(100) UNIQUE NOT NULL,
    origin VARCHAR(255),
    destination VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Shipment Events table
CREATE TABLE shipment_events (
    id SERIAL PRIMARY KEY,
    shipment_id INTEGER REFERENCES shipments(id),
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    location VARCHAR(255),
    raw_status_text TEXT,
    ai_status VARCHAR(50),
    ai_reason VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8)
);

-- Performance indexes
CREATE INDEX idx_shipment_id ON shipment_events(shipment_id);
CREATE INDEX idx_ai_status ON shipment_events(ai_status);
CREATE INDEX idx_coordinates ON shipment_events(latitude, longitude);
CREATE INDEX idx_timestamp ON shipment_events(timestamp);
```

---

## 🐛 Troubleshooting

### No data on map?
1. Check backend logs on Render for worker activity
2. Verify `USE_AIS_API=true` and `ENABLE_BACKGROUND_WORKER=true`
3. Wait 5-15 minutes for AIS data to populate
4. Try Singapore bounding box (busiest area)
5. Test with mock mode: `USE_AIS_API=false`

### Backend sleeping (Render free tier)?
- First request after 15 min takes 30-60 seconds to wake up
- Use [UptimeRobot](https://uptimerobot.com) to ping every 5 min (keeps it awake)
- Or upgrade to Render paid tier ($7/month for always-on)

### Database connection issues?
- Verify `DATABASE_URL` format: `postgresql://user:pass@host/db`
- Check Neon database is not paused (free tier auto-pauses)
- Ensure `?sslmode=require` is in connection string
- Test connection: Visit database health endpoint above

### Worker not ingesting data?
- Check `ENABLE_BACKGROUND_WORKER=true` in Render env vars
- Verify AISStream API key is valid
- Check bounding box has ship traffic
- View Render logs for WebSocket connection status

### Frontend errors?
- Ensure `API_URL` points to correct backend URL
- Check backend is awake (visit health endpoint)
- Verify Streamlit Cloud has correct secrets configured

---

## 🤝 Contributing

Contributions welcome! Please:
1. Fork the repository
2. Create feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Open Pull Request

---

## 📝 License

This project is open source and available under the [MIT License](LICENSE).

---

## 👨‍💻 Author

**Manush Patel**

- 🌐 GitHub: [@ManushPatel08](https://github.com/ManushPatel08)
- 💼 LinkedIn: [manush-patel08](https://linkedin.com/in/manush-patel08)

---

## 🙏 Acknowledgments

- [AISStream.io](https://aisstream.io) - Real-time maritime AIS data
- [Hugging Face](https://huggingface.co) - AI/ML model inference
- [FastAPI](https://fastapi.tiangolo.com) - Modern web framework
- [Streamlit](https://streamlit.io) - Rapid dashboard development
- [Neon](https://neon.tech) - Serverless PostgreSQL
- [Render](https://render.com) - Cloud application platform
- [Plotly](https://plotly.com) - Interactive visualizations

---

⭐ **Star this repo if you find it useful!**

**Built with ❤️ by Manush Patel**
