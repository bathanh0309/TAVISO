"""
Traffic Violation Detection Service
Combines vehicle detection, tracking, and violation analysis
"""
from datetime import datetime
import yaml

class ViolationDetector:
    """
    Detect traffic violations by analyzing vehicle tracks
    """
    
    VIOLATION_TYPES = {
        'wrong_way': 'Đi ngược chiều',
        'speeding': 'Vượt tốc độ', 
        'line_crossing': 'Vượt vạch'
    }
    
    def __init__(self, config_path='config/settings.yaml'):
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        violation_config = self.config.get('violation', {})
        
        self.enable_wrong_way = violation_config.get('enable_wrong_way', True)
        self.enable_speeding = violation_config.get('enable_speeding', True)
        self.enable_line_crossing = violation_config.get('enable_line_crossing', False)
        self.speed_limit = violation_config.get('speed_limit_kmh', 40)
        self.expected_direction = violation_config.get('expected_direction', 'down')
        
        # For line crossing (can be configured via API)
        self.detection_line_y = None
        
        print(f"✓ ViolationDetector initialized")
        print(f"  - Wrong-way detection: {'ON' if self.enable_wrong_way else 'OFF'}")
        print(f"  - Speed limit: {self.speed_limit} km/h")
        print(f"  - Expected direction: {self.expected_direction}")
    
    def analyze_tracks(self, tracker, detector, frame, db=None, logger=None):
        """
        Analyze all tracks for violations
        
        Args:
            tracker: VehicleTracker instance
            detector: LicensePlateDetector instance
            frame: Current video frame
            db: Database session (optional, for logging)
            logger: DetectionLogger instance (optional)
        
        Returns:
            list: List of detected violations [{track_id, type, plate, confidence, ...}]
        """
        violations = []
        
        # Get all active tracks
        all_violations = tracker.get_all_violations()
        
        for track_id in list(tracker.tracks.keys()):
            # Skip if already recorded this violation
            if track_id in all_violations:
                continue
            
            violation = self._check_track_for_violation(tracker, track_id)
            
            if violation:
                # Try to read license plate
                plate = tracker.get_license_plate(track_id)
                
                if not plate:
                    # Try to read from current frame
                    positions = tracker.tracks[track_id]['positions']
                    if positions:
                        # Get approximate bbox from last few positions
                        # This is a rough estimate since we don't have exact bbox here
                        last_pos = positions[-1]
                        # Create a region around the last position
                        bbox = (
                            last_pos[0] - 100,
                            last_pos[1] - 100,
                            last_pos[0] + 100,
                            last_pos[1] + 100
                        )
                        plate = detector.read_plate_from_vehicle(frame, bbox)
                        if plate:
                            tracker.set_license_plate(track_id, plate)
                
                # Record violation
                tracker.set_violation(track_id, violation['type'])
                
                violation['license_plate'] = plate
                violation['track_id'] = track_id
                violation['timestamp'] = datetime.now()
                violation['vehicle_type'] = tracker.tracks[track_id].get('class_name', 'vehicle')
                
                violations.append(violation)
                
                # Log to database if available
                if db and logger:
                    logger.log_violation(
                        db=db,
                        violation_type=violation['type'],
                        license_plate=plate,
                        confidence=violation.get('confidence', 0.8),
                        speed_kmh=violation.get('speed'),
                        vehicle_type=violation['vehicle_type'],
                        track_id=track_id,
                        frame=frame
                    )
        
        return violations
    
    def _check_track_for_violation(self, tracker, track_id):
        """
        Check a single track for any violations
        
        Returns:
            dict: Violation info or None
        """
        # Check wrong-way
        if self.enable_wrong_way:
            if tracker.check_wrong_way(track_id, self.expected_direction):
                return {
                    'type': 'wrong_way',
                    'confidence': 0.85
                }
        
        # Check speeding
        if self.enable_speeding:
            speed = tracker.calculate_speed(track_id)
            if speed and speed > self.speed_limit:
                return {
                    'type': 'speeding',
                    'speed': speed,
                    'confidence': 0.8
                }
        
        # Check line crossing
        if self.enable_line_crossing and self.detection_line_y:
            if tracker.check_line_crossing(track_id, self.detection_line_y):
                return {
                    'type': 'line_crossing',
                    'confidence': 0.9
                }
        
        return None
    
    def set_detection_line(self, y_position):
        """Set virtual detection line for line crossing"""
        self.detection_line_y = y_position
        print(f"Detection line set at Y={y_position}")
    
    def get_violation_summary(self, violations):
        """
        Get summary of violations for display
        
        Args:
            violations: List of violation dicts
        
        Returns:
            list: Formatted for realtime display
        """
        summary = []
        for v in violations:
            summary.append({
                'id': v.get('track_id'),
                'date': v['timestamp'].strftime('%d/%m/%Y'),
                'time': v['timestamp'].strftime('%H:%M'),
                'license_plate': v.get('license_plate') or 'Không rõ',
                'violation_type': self.VIOLATION_TYPES.get(v['type'], v['type']),
                'speed': v.get('speed')
            })
        return summary
