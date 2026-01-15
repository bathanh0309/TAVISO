"""
Database models for traffic violation detection
"""
from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from backend.database import Base

class LicensePlate(Base):
    """License plate detection record"""
    __tablename__ = "license_plates"

    id = Column(Integer, primary_key=True, index=True)
    plate_number = Column(String, index=True, nullable=False)
    timestamp = Column(DateTime, default=datetime.now, index=True)
    confidence = Column(Float, nullable=False)
    image_path = Column(String, nullable=True)
    
    def __repr__(self):
        return f"<LicensePlate(plate={self.plate_number}, time={self.timestamp})>"
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            "id": self.id,
            "plate_number": self.plate_number,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "confidence": round(self.confidence, 2),
            "image_path": self.image_path
        }


class TrafficViolation(Base):
    """Traffic violation record"""
    __tablename__ = "traffic_violations"

    id = Column(Integer, primary_key=True, index=True)
    license_plate = Column(String, index=True, nullable=True)  # May be unknown
    violation_type = Column(String, nullable=False)  # wrong_way, speeding, line_crossing
    timestamp = Column(DateTime, default=datetime.now, index=True)
    confidence = Column(Float, nullable=False)
    speed_kmh = Column(Float, nullable=True)  # For speeding violations
    vehicle_type = Column(String, nullable=True)  # car, motorcycle, truck, bus
    track_id = Column(Integer, nullable=True)  # DeepSORT track ID
    image_path = Column(String, nullable=True)  # Screenshot of violation
    
    def __repr__(self):
        return f"<TrafficViolation(type={self.violation_type}, plate={self.license_plate}, time={self.timestamp})>"
    
    def to_dict(self):
        """Convert to dictionary for JSON response"""
        return {
            "id": self.id,
            "license_plate": self.license_plate or "Không rõ",
            "violation_type": self.violation_type,
            "violation_type_vi": self._get_violation_type_vi(),
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "date": self.timestamp.strftime("%d/%m/%Y") if self.timestamp else None,
            "time": self.timestamp.strftime("%H:%M:%S") if self.timestamp else None,
            "confidence": round(self.confidence, 2),
            "speed_kmh": self.speed_kmh,
            "vehicle_type": self.vehicle_type,
            "track_id": self.track_id,
            "image_path": self.image_path
        }
    
    def _get_violation_type_vi(self):
        """Get Vietnamese name for violation type"""
        types = {
            "wrong_way": "Đi ngược chiều",
            "speeding": "Vượt tốc độ",
            "line_crossing": "Vượt vạch",
            "red_light": "Vượt đèn đỏ"
        }
        return types.get(self.violation_type, self.violation_type)
