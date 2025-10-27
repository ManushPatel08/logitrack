# --- IMPORTS ---
from fastapi import FastAPI, Depends
from sqlmodel import Session, select, func
from sqlalchemy.sql import text
from typing import List

# --- LOCAL IMPORTS ---
from database import get_session
from models import DelayReasonKPI, Shipment, ShipmentEvent, ShipmentLiveLocation

# --- FASTAPI APP ---
app = FastAPI(title="LogiTrack AI API")

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

# --- KPI ENDPOINT ---
@app.get("/api/v1/kpi/delay_reasons", response_model=List[DelayReasonKPI], tags=["KPIs"])
def get_delay_reasons(session: Session = Depends(get_session)):
    """Get the count of all shipments grouped by delay reason."""
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
    """Get all shipments that are currently marked as 'Delayed'."""
    subquery = (
        select(ShipmentEvent.shipment_id)
        .where(ShipmentEvent.ai_status == "Delayed")
        .distinct()
    )
    statement = select(Shipment).where(Shipment.id.in_(subquery))
    results = session.exec(statement).all()
    return results

# --- LIVE LOCATIONS ENDPOINT (UPDATED WITH COORDINATES) ---
@app.get("/api/v1/shipments/live_locations", response_model=List[ShipmentLiveLocation], tags=["Shipments"])
def get_live_locations(session: Session = Depends(get_session)):
    """Get the single, most recent event for every non-delivered shipment with coordinates."""
    raw_query = text("""
        SELECT DISTINCT ON (s.id)
            s.id as shipment_id,
            s.tracking_id,
            e.location,
            e.ai_status,
            e.timestamp,
            e.latitude,
            e.longitude
        FROM shipments s
        JOIN shipment_events e ON s.id = e.shipment_id
        WHERE e.ai_status IS NULL OR e.ai_status != 'Delivered'
        ORDER BY s.id, e.timestamp DESC;
    """)
    results = session.exec(raw_query).all()
    
    return [
        ShipmentLiveLocation(
            shipment_id=row.shipment_id,
            tracking_id=row.tracking_id,
            location=row.location,
            ai_status=row.ai_status,
            timestamp=row.timestamp,
            latitude=float(row.latitude) if row.latitude else None,
            longitude=float(row.longitude) if row.longitude else None
        ) for row in results
    ]
