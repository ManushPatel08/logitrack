from sqlmodel import SQLModel, Field
from typing import Optional
import datetime
from decimal import Decimal

class DelayReasonKPI(SQLModel):
    """Model for the delay_reasons KPI"""
    ai_reason: Optional[str] = "N/A"
    count: int

class Shipment(SQLModel, table=True):
    """Database model for a Shipment"""
    __tablename__ = "shipments"

    id: Optional[int] = Field(default=None, primary_key=True)
    tracking_id: str
    origin: Optional[str] = None
    destination: Optional[str] = None

class ShipmentEvent(SQLModel, table=True):
     __tablename__ = "shipment_events"
     id: Optional[int] = Field(default=None, primary_key=True)
     shipment_id: Optional[int] = Field(default=None, foreign_key="shipments.id")
     timestamp: Optional[datetime.datetime] = None
     location: Optional[str] = None
     raw_status_text: Optional[str] = None
     ai_status: Optional[str] = None
     ai_reason: Optional[str] = None
     latitude: Optional[Decimal] = None
     longitude: Optional[Decimal] = None

class ShipmentLiveLocation(SQLModel):
    """Model for the live map response"""
    shipment_id: int
    tracking_id: str
    location: Optional[str] = None
    ai_status: Optional[str] = None
    timestamp: Optional[datetime.datetime] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
