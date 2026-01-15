"""
Logger service for saving detection and violation records to database and CSV
"""
import csv
import os
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from backend.models import LicensePlate, TrafficViolation
import yaml
import cv2

class DetectionLogger:
    """Log license plate detections and traffic violations to database and CSV"""
    
    def __init__(self, config_path='config/settings.yaml'):
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.csv_path = self.config['csv']['path']
        self.cooldown_seconds = self.config['detection']['cooldown_seconds']
        self.save_crops = self.config['detection']['save_crops']
        self.crops_dir = self.config['detection']['crops_dir']
        
        # Violation-specific paths
        storage_config = self.config.get('storage', {})
        self.save_images = storage_config.get('save_images', True)
        self.images_dir = storage_config.get('images_dir', 'data/images')
        
        # Create directories
        os.makedirs(os.path.dirname(self.csv_path), exist_ok=True)
        if self.save_crops:
            os.makedirs(self.crops_dir, exist_ok=True)
        if self.save_images:
            os.makedirs(self.images_dir, exist_ok=True)
        
        # Initialize CSV files
        self._init_csv()
        self._init_violation_csv()
        
        # Track recent detections to avoid duplicates
        self.recent_detections = {}  # {plate_number: timestamp}
        self.recent_violations = {}  # {track_id: timestamp}
        
        print("✓ Logger initialized")
    
    def _init_csv(self):
        """Initialize CSV file with headers if it doesn't exist"""
        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['ID', 'Plate Number', 'Timestamp', 'Confidence', 'Image Path'])
    
    def _init_violation_csv(self):
        """Initialize violation CSV file"""
        violation_csv = self.csv_path.replace('.csv', '_violations.csv')
        if not os.path.exists(violation_csv):
            with open(violation_csv, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'ID', 'License Plate', 'Violation Type', 'Date', 'Time',
                    'Confidence', 'Speed (km/h)', 'Vehicle Type', 'Track ID', 'Image Path'
                ])
        self.violation_csv_path = violation_csv
    
    def should_log(self, plate_number):
        """Check if we should log this detection (avoid spam)"""
        now = datetime.now()
        
        if plate_number in self.recent_detections:
            last_time = self.recent_detections[plate_number]
            if (now - last_time).total_seconds() < self.cooldown_seconds:
                return False
        
        self.recent_detections[plate_number] = now
        return True
    
    def should_log_violation(self, track_id):
        """Check if we should log this violation (avoid duplicate violations)"""
        now = datetime.now()
        
        if track_id in self.recent_violations:
            last_time = self.recent_violations[track_id]
            if (now - last_time).total_seconds() < self.cooldown_seconds * 2:
                return False
        
        self.recent_violations[track_id] = now
        return True
    
    def log_detection(self, db: Session, plate_number, confidence, crop_image=None):
        """Log detection to database and CSV"""
        if not self.should_log(plate_number):
            return None
        
        timestamp = datetime.now()
        
        # Save crop image
        image_path = None
        if crop_image is not None and self.save_crops:
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
        
        print(f"✓ Logged plate: {plate_number} at {timestamp.strftime('%H:%M:%S')}")
        
        return record

    def log_violation(self, db: Session, violation_type, license_plate=None, 
                      confidence=0.8, speed_kmh=None, vehicle_type=None,
                      track_id=None, frame=None):
        """
        Log traffic violation to database and CSV
        
        Args:
            db: Database session
            violation_type: Type of violation (wrong_way, speeding, line_crossing)
            license_plate: License plate number (may be None)
            confidence: Detection confidence
            speed_kmh: Vehicle speed if applicable
            vehicle_type: Type of vehicle
            track_id: DeepSORT track ID
            frame: Current frame for screenshot
        
        Returns:
            TrafficViolation: Created database record
        """
        # Check cooldown for this track
        if track_id and not self.should_log_violation(track_id):
            return None
        
        timestamp = datetime.now()
        
        # Save violation screenshot
        image_path = None
        if frame is not None and self.save_images:
            plate_str = license_plate.replace('-', '').replace('.', '') if license_plate else 'unknown'
            filename = f"violation_{violation_type}_{plate_str}_{timestamp.strftime('%Y%m%d_%H%M%S')}.jpg"
            image_path = os.path.join(self.images_dir, filename)
            cv2.imwrite(image_path, frame)
        
        # Save to database
        record = TrafficViolation(
            license_plate=license_plate,
            violation_type=violation_type,
            timestamp=timestamp,
            confidence=confidence,
            speed_kmh=speed_kmh,
            vehicle_type=vehicle_type,
            track_id=track_id,
            image_path=image_path
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        
        # Append to CSV
        with open(self.violation_csv_path, 'a', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([
                record.id,
                license_plate or 'Không rõ',
                violation_type,
                timestamp.strftime('%d/%m/%Y'),
                timestamp.strftime('%H:%M:%S'),
                f"{confidence:.2%}",
                f"{speed_kmh:.1f}" if speed_kmh else '',
                vehicle_type or '',
                track_id or '',
                image_path or ''
            ])
        
        # Print violation alert
        violation_vi = {
            'wrong_way': 'Đi ngược chiều',
            'speeding': 'Vượt tốc độ',
            'line_crossing': 'Vượt vạch'
        }.get(violation_type, violation_type)
        
        print(f"⚠️ VI PHẠM: {violation_vi} | Biển số: {license_plate or 'Không rõ'} | {timestamp.strftime('%H:%M:%S')}")
        
        return record
    
    def cleanup_old_detections(self):
        """Remove old entries from tracking dicts"""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.cooldown_seconds * 2)
        
        # Cleanup plate detections
        to_remove = [
            plate for plate, timestamp in self.recent_detections.items()
            if timestamp < cutoff
        ]
        for plate in to_remove:
            del self.recent_detections[plate]
        
        # Cleanup violations
        to_remove = [
            track_id for track_id, timestamp in self.recent_violations.items()
            if timestamp < cutoff
        ]
        for track_id in to_remove:
            del self.recent_violations[track_id]
