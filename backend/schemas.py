"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class LicensePlateBase(BaseModel):
    plate_number: str
    confidence: float

class LicensePlateCreate(LicensePlateBase):
    image_path: Optional[str] = None

class LicensePlateResponse(LicensePlateBase):
    id: int
    timestamp: datetime
    image_path: Optional[str] = None
    
    class Config:
        from_attributes = True

class StatsResponse(BaseModel):
    total_detections: int
    today_detections: int
    this_hour_detections: int
    last_detection: Optional[datetime] = None
    unique_plates: int
