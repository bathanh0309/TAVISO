"""
Logger service for saving detection records to database and CSV
"""
import csv
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import LicensePlate
import yaml

class DetectionLogger:
    """Log license plate detections to database and CSV"""
    
    def __init__(self, config_path='config/settings.yaml'):
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.csv_path = self.config['csv']['path']
        self.cooldown_seconds = self.config['detection']['cooldown_seconds']
        self.save_crops = self.config['detection']['save_crops']
        self.crops_dir = self.config['detection']['crops_dir']
        
        # Create directories
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        if self.save_crops:
            os.makedirs(self.crops_dir, exist_ok=True)
        
        # Initialize CSV if not exists
        self._init_csv()
        
        # Track recent detections to avoid duplicates
        self.recent_detections = {}  # {plate_number: timestamp}
    
    def _init_csv(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Plate Number', 'Timestamp', 'Confidence', 'Image Path'])
    
    def should_log(self, plate_number):
        """
        Check if we should log this detection (avoid spam from same car)
        
        Args:
            plate_number: The plate number
        
        Returns:
            bool: True if should log, False if too recent
        """
        now = datetime.now()
        
        if plate_number in self.recent_detections:
            last_time = self.recent_detections[plate_number]
            if (now - last_time).total_seconds() < self.cooldown_seconds:
                return False
        
        self.recent_detections[plate_number] = now
        return True
    
    def log_detection(self, db: Session, plate_number, confidence, crop_image=None):
        """
        Log detection to database and CSV
        
        Args:
            db: Database session
            plate_number: Detected plate number
            confidence: Detection confidence
            crop_image: Optional cropped plate image
        
        Returns:
            LicensePlate: Created database record
        """
        # Check cooldown
        if not self.should_log(plate_number):
            return None
        
        timestamp = datetime.now()
        
        # Save crop image if available
        image_path = None
        if crop_image is not None and self.save_crops:
            import cv2
            filename = f"{plate_number}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            image_path = os.path.join(self.crops_dir, filename)
            cv2.imwrite(image_path, crop_image)
        
        # Save to database
        record = LicensePlate(
            plate_number=plate_number,
            timestamp=timestamp,
            confidence=confidence,
            image_path=image_path
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        
        # Append to CSV
        with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                record.id,
                plate_number,
                timestamp.strftime('%Y-%m-%d %H:%M:%S'),
                f"{confidence:.2%}",
                image_path or ''
            ])
        
        print(f"✓ Logged: {plate_number} at {timestamp.strftime('%H:%M:%S')}")
        
        return record
    
    def cleanup_old_detections(self):
        """Remove old entries from recent_detections dict"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.cooldown_seconds * 2)
        
        to_remove = [
            plate for plate, timestamp in self.recent_detections.items()
            if timestamp < cutoff
        ]
        
        for plate in to_remove:
            del self.recent_detections[plate]
