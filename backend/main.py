# --- IMPORTS ---
from fastapi import FastAPI, Depends, Query
import os
from sqlmodel import Session, select, func
from sqlalchemy.sql import text
from typing import List

# --- LOCAL IMPORTS ---
from database import get_session
from models import DelayReasonKPI, Shipment, ShipmentEvent, ShipmentLiveLocation

# --- FASTAPI APP ---
app = FastAPI(title="LogiTrack AI API")

# --- START BACKGROUND WORKER (if enabled) ---
from background_worker import start_background_worker

@app.on_event("startup")
async def startup_event():
    """Start background worker on API startup."""
    start_background_worker()

# --- CONFIG: control mock visibility from env ---
def _as_bool(val: str) -> bool:
    """Interpret common truthy strings as boolean True."""
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}

# If any of these are true => hide mock data on dashboard (per requirement):
# - MOCK_DATA_INGEST (requested name)
# - DISABLE_MOCK_INGEST (existing worker flag)
# Otherwise show mock data.
# We also keep compatibility with previous EXCLUDE_MOCK_PREFIX/MOCK_PREFIX variables.
_mock_ingest_flag = (
    os.environ.get("MOCK_DATA_INGEST")
    or os.environ.get("mock_data_ingest")
    or os.environ.get("DISABLE_MOCK_INGEST")
    or os.environ.get("disable_mock_ingest")
    or ""
).strip()
_hide_mock = _as_bool(_mock_ingest_flag)

# Determine the mock tracking_id prefix
_mock_prefix = (
    os.environ.get("MOCK_PREFIX")
    or os.environ.get("EXCLUDE_MOCK_PREFIX")
    or "SHP"
)

# Effective prefix to exclude (empty string means no exclusion)
EXCLUDE_MOCK_PREFIX = _mock_prefix.strip() if _hide_mock else ""

# --- HEALTH ENDPOINTS ---
@app.get("/health", tags=["Health"])
def health_check():
    """Check if the API is running."""
    return {"status": "ok"}

@app.get("/health/db", tags=["Health"])
def db_health_check(session: Session = Depends(get_session)):
    """Check if the API can connect to the database."""
    try:
        session.exec(select(1))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "database": "connection_failed", "detail": str(e)}

# --- DEBUG CONFIG ENDPOINT ---
@app.get("/debug/config", tags=["Debug"])
def debug_config():
    """Return effective mock filtering config for troubleshooting."""
    return {
        "MOCK_DATA_INGEST": os.environ.get("MOCK_DATA_INGEST"),
        "mock_data_ingest": os.environ.get("mock_data_ingest"),
        "DISABLE_MOCK_INGEST": os.environ.get("DISABLE_MOCK_INGEST"),
        "disable_mock_ingest": os.environ.get("disable_mock_ingest"),
        "MOCK_PREFIX": os.environ.get("MOCK_PREFIX"),
        "EXCLUDE_MOCK_PREFIX_env": os.environ.get("EXCLUDE_MOCK_PREFIX"),
        "_hide_mock": _hide_mock,
        "EXCLUDE_MOCK_PREFIX_effective": EXCLUDE_MOCK_PREFIX,
    }

# --- KPI ENDPOINT ---
@app.get("/api/v1/kpi/delay_reasons", response_model=List[DelayReasonKPI], tags=["KPIs"])
def get_delay_reasons(session: Session = Depends(get_session)):
    """Get the count of all shipments grouped by delay reason."""
    # Optionally exclude mock shipments by prefix
    if EXCLUDE_MOCK_PREFIX:
        statement = (
            select(ShipmentEvent.ai_reason, func.count().label("count"))
            .join(Shipment, Shipment.id == ShipmentEvent.shipment_id)
            .where(ShipmentEvent.ai_status == "Delayed")
            .where(~Shipment.tracking_id.startswith(EXCLUDE_MOCK_PREFIX))
            .group_by(ShipmentEvent.ai_reason)
        )
    else:
        statement = (
            select(ShipmentEvent.ai_reason, func.count().label("count"))
            .where(ShipmentEvent.ai_status == "Delayed")
            .group_by(ShipmentEvent.ai_reason)
        )
    results = session.exec(statement).all()
    return [{"ai_reason": reason if reason else "N/A", "count": count} for reason, count in results]

# --- AT-RISK SHIPMENTS ENDPOINT ---
@app.get("/api/v1/shipments/at_risk", response_model=List[Shipment], tags=["Shipments"])
def get_at_risk_shipments(session: Session = Depends(get_session)):
    """Get shipments whose most recent event is currently 'Delayed'.

    This aligns with the dashboard's "At Risk" metric so it won't exceed
    the count of active shipments.
    """
    if EXCLUDE_MOCK_PREFIX:
        raw_query = text(
            """
            SELECT s.*
            FROM shipments s
            JOIN (
                SELECT DISTINCT ON (shipment_id)
                    shipment_id, ai_status, timestamp
                FROM shipment_events
                ORDER BY shipment_id, timestamp DESC
            ) e ON e.shipment_id = s.id
            WHERE e.ai_status = 'Delayed'
              AND s.tracking_id NOT LIKE :mock_prefix
            """
        )
        results = session.exec(raw_query, params={"mock_prefix": f"{EXCLUDE_MOCK_PREFIX}%"}).all()
    else:
        raw_query = text(
            """
            SELECT s.*
            FROM shipments s
            JOIN (
                SELECT DISTINCT ON (shipment_id)
                    shipment_id, ai_status, timestamp
                FROM shipment_events
                ORDER BY shipment_id, timestamp DESC
            ) e ON e.shipment_id = s.id
            WHERE e.ai_status = 'Delayed'
            """
        )
        results = session.exec(raw_query).all()
    return results

# --- LIVE LOCATIONS ENDPOINT (UPDATED WITH COORDINATES) ---
@app.get("/api/v1/shipments/live_locations", response_model=List[ShipmentLiveLocation], tags=["Shipments"])
def get_live_locations(
    session: Session = Depends(get_session),
    limit: int = Query(1000, ge=1, le=20000, description="Maximum number of shipments to return"),
):
    """Get the single, most recent event for every non-delivered shipment with coordinates.

    Supports limiting the number of shipments returned to reduce payload size and improve latency.
    """
    if EXCLUDE_MOCK_PREFIX:
        raw_query = text(
            """
            SELECT * FROM (
                SELECT DISTINCT ON (s.id)
                    s.id as shipment_id,
                    s.tracking_id,
                    e.location,
                    e.ai_status AS ai_category,
                    COALESCE(e.ai_reason, e.raw_status_text, e.ai_status) AS ai_text,
                    e.timestamp,
                    e.latitude,
                    e.longitude
                FROM shipments s
                JOIN shipment_events e ON s.id = e.shipment_id
                WHERE (e.ai_status IS NULL OR e.ai_status != 'Delivered')
                  AND s.tracking_id NOT LIKE :mock_prefix
                ORDER BY s.id, e.timestamp DESC
            ) t
            LIMIT :limit;
            """
        )
        stmt = raw_query.bindparams(mock_prefix=f"{EXCLUDE_MOCK_PREFIX}%", limit=limit)
        results = session.exec(stmt).all()
    else:
        raw_query = text(
            """
            SELECT * FROM (
                SELECT DISTINCT ON (s.id)
                    s.id as shipment_id,
                    s.tracking_id,
                    e.location,
                    e.ai_status AS ai_category,
                    COALESCE(e.ai_reason, e.raw_status_text, e.ai_status) AS ai_text,
                    e.timestamp,
                    e.latitude,
                    e.longitude
                FROM shipments s
                JOIN shipment_events e ON s.id = e.shipment_id
                WHERE e.ai_status IS NULL OR e.ai_status != 'Delivered'
                ORDER BY s.id, e.timestamp DESC
            ) t
            LIMIT :limit;
            """
        )
        results = session.exec(raw_query, params={"limit": limit}).all()
    
    payload = []
    for row in results:
        # Back-compat: ai_status mirrors ai_text so existing UI keeps working
        ai_text = getattr(row, "ai_text", None)
        ai_category = getattr(row, "ai_category", None)
        payload.append(
            ShipmentLiveLocation(
                shipment_id=row.shipment_id,
                tracking_id=row.tracking_id,
                location=row.location,
                ai_status=ai_text if ai_text else ai_category,
                ai_text=ai_text,
                ai_category=ai_category,
                timestamp=row.timestamp,
                latitude=float(row.latitude) if row.latitude else None,
                longitude=float(row.longitude) if row.longitude else None,
            )
        )
    return payload
