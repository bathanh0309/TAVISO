"""
Pydantic schemas for request/response validation
"""
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List

# License Plate Schemas
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


# Traffic Violation Schemas
class ViolationBase(BaseModel):
    license_plate: Optional[str] = None
    violation_type: str
    confidence: float

class ViolationCreate(ViolationBase):
    speed_kmh: Optional[float] = None
    vehicle_type: Optional[str] = None
    track_id: Optional[int] = None
    image_path: Optional[str] = None

class ViolationResponse(BaseModel):
    id: int
    license_plate: str
    violation_type: str
    violation_type_vi: str
    timestamp: datetime
    date: str
    time: str
    confidence: float
    speed_kmh: Optional[float] = None
    vehicle_type: Optional[str] = None
    track_id: Optional[int] = None
    image_path: Optional[str] = None
    
    class Config:
        from_attributes = True


# Statistics Schemas
class StatsResponse(BaseModel):
    total_detections: int
    today_detections: int
    this_hour_detections: int
    last_detection: Optional[datetime] = None
    unique_plates: int

class ViolationStatsResponse(BaseModel):
    total_violations: int
    today_violations: int
    this_hour_violations: int
    wrong_way_count: int
    speeding_count: int
    line_crossing_count: int
    last_violation: Optional[ViolationResponse] = None


# Realtime Response
class RealtimeViolation(BaseModel):
    """Single violation for realtime display"""
    id: int
    date: str
    time: str
    license_plate: str
    violation_type_vi: str
    confidence: float

class RealtimeResponse(BaseModel):
    """Response for realtime violations endpoint"""
    violations: List[RealtimeViolation]
    total_count: int
