"""
Database models for license plate records
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
