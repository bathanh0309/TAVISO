"""
Object tracking service using DeepSORT with violation detection
"""
from deep_sort_realtime.deepsort_tracker import DeepSort
import numpy as np
import time

class VehicleTracker:
    """
    Track vehicles across frames using DeepSORT and detect violations
    """
    def __init__(self, max_age=30, n_init=3):
        print("Initializing DeepSORT tracker...")
        self.tracker = DeepSort(
            max_age=max_age,
            n_init=n_init,
            max_iou_distance=0.7,
            nms_max_overlap=1.0, 
            max_cosine_distance=0.2,
            nn_budget=None,
            override_track_class=None,
            embedder="mobilenet",
            half=True,
            bgr=True,
            embedder_gpu=False
        )
        self.tracks = {}  # History of tracks {track_id: {'positions': [], 'timestamps': [], 'plate': None}}
        self.violations = {}  # {track_id: {'type': str, 'detected_at': timestamp}}
        self.fps = 15  # Assumed FPS for speed calculation
        self.pixels_per_meter = 10  # Calibration value (adjust based on camera)
        print("✓ Tracker initialized")

    def update(self, detections, frame):
        """
        Update tracks with new detections
        
        Args:
            detections: List of dicts from detector [{bbox, confidence, class_id, class_name}]
            frame: Current video frame
            
        Returns:
            list: List of active tracks with track_id
        """
        # Format for DeepSORT: [[left, top, w, h], confidence, detection_class]
        bbs = []
        det_info = []  # Keep detection info for later
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            w = x2 - x1
            h = y2 - y1
            conf = det['confidence']
            class_id = det.get('class_id', 0)
            bbs.append([[x1, y1, w, h], conf, class_id])
            det_info.append(det)
            
        # Update tracker
        tracks = self.tracker.update_tracks(bbs, frame=frame)
        
        results = []
        current_time = time.time()
        
        for track in tracks:
            if not track.is_confirmed():
                continue
                
            track_id = track.track_id
            ltrb = track.to_ltrb()  # [left, top, right, bottom]
            
            # Calculate center point
            center_x = int((ltrb[0] + ltrb[2]) / 2)
            center_y = int((ltrb[1] + ltrb[3]) / 2)
            
            # Initialize track history if new
            if track_id not in self.tracks:
                self.tracks[track_id] = {
                    'positions': [],
                    'timestamps': [],
                    'plate': None,
                    'class_name': None
                }
            
            # Store position and timestamp
            self.tracks[track_id]['positions'].append((center_x, center_y))
            self.tracks[track_id]['timestamps'].append(current_time)
            
            # Keep only last 100 points
            if len(self.tracks[track_id]['positions']) > 100:
                self.tracks[track_id]['positions'].pop(0)
                self.tracks[track_id]['timestamps'].pop(0)
            
            # Find matching detection to get class info
            class_name = 'vehicle'
            confidence = 0.5  # Default confidence
            for det in det_info:
                dx1, dy1, dx2, dy2 = det['bbox']
                det_cx = (dx1 + dx2) / 2
                det_cy = (dy1 + dy2) / 2
                if abs(det_cx - center_x) < 50 and abs(det_cy - center_y) < 50:
                    class_name = det.get('class_name', 'vehicle')
                    confidence = det.get('confidence', 0.5)
                    self.tracks[track_id]['class_name'] = class_name
                    break
                    
            results.append({
                'track_id': track_id,
                'bbox': [int(x) for x in ltrb],
                'confidence': confidence,
                'class_name': self.tracks[track_id].get('class_name', class_name),
                'history': self.tracks[track_id]['positions'][-20:],  # Last 20 positions
                'plate_number': self.tracks[track_id].get('plate')
            })
            
        return results
    
    def set_license_plate(self, track_id, plate_number):
        """Associate a license plate with a track"""
        if track_id in self.tracks:
            self.tracks[track_id]['plate'] = plate_number
    
    def get_license_plate(self, track_id):
        """Get license plate for a track"""
        if track_id in self.tracks:
            return self.tracks[track_id].get('plate')
        return None

    def check_wrong_way(self, track_id, expected_direction="down"):
        """
        Check if vehicle is moving in wrong direction
        
        Args:
            track_id: ID of the track to check
            expected_direction: Expected valid direction ("down", "up", "left", "right")
            
        Returns:
            bool: True if wrong way detected
        """
        if track_id not in self.tracks:
            return False
            
        positions = self.tracks[track_id]['positions']
        if len(positions) < 15:  # Need enough points
            return False
            
        # Compare first and last points
        start = positions[0]
        end = positions[-1]
        
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        
        # Minimum movement threshold (pixels)
        min_movement = 30
        
        if abs(dx) < min_movement and abs(dy) < min_movement:
            return False
            
        if expected_direction == "down":
            return dy < -min_movement  # Moving up is wrong
        elif expected_direction == "up":
            return dy > min_movement   # Moving down is wrong
        elif expected_direction == "right":
            return dx < -min_movement  # Moving left is wrong
        elif expected_direction == "left":
            return dx > min_movement   # Moving right is wrong
            
        return False
    
    def calculate_speed(self, track_id):
        """
        Estimate vehicle speed in km/h
        
        Args:
            track_id: ID of the track
            
        Returns:
            float: Estimated speed in km/h, or None if cannot calculate
        """
        if track_id not in self.tracks:
            return None
            
        positions = self.tracks[track_id]['positions']
        timestamps = self.tracks[track_id]['timestamps']
        
        if len(positions) < 5:
            return None
        
        # Calculate distance over last N frames
        n = min(10, len(positions))
        start_pos = positions[-n]
        end_pos = positions[-1]
        start_time = timestamps[-n]
        end_time = timestamps[-1]
        
        # Pixel distance
        dx = end_pos[0] - start_pos[0]
        dy = end_pos[1] - start_pos[1]
        pixel_distance = np.sqrt(dx**2 + dy**2)
        
        # Time elapsed
        time_elapsed = end_time - start_time
        if time_elapsed <= 0:
            return None
        
        # Convert to real-world speed
        # meters = pixels / pixels_per_meter
        distance_meters = pixel_distance / self.pixels_per_meter
        
        # m/s to km/h
        speed_mps = distance_meters / time_elapsed
        speed_kmh = speed_mps * 3.6
        
        return speed_kmh
    
    def check_line_crossing(self, track_id, line_y):
        """
        Check if vehicle crossed a virtual line
        
        Args:
            track_id: ID of the track
            line_y: Y coordinate of the line
            
        Returns:
            bool: True if line was crossed
        """
        if track_id not in self.tracks:
            return False
            
        positions = self.tracks[track_id]['positions']
        if len(positions) < 3:
            return False
        
        # Check if trajectory crosses the line
        for i in range(1, len(positions)):
            prev_y = positions[i-1][1]
            curr_y = positions[i][1]
            
            # Check if crossed the line
            if (prev_y < line_y and curr_y >= line_y) or (prev_y > line_y and curr_y <= line_y):
                return True
        
        return False
    
    def get_violation(self, track_id):
        """Get violation info for a track if any"""
        return self.violations.get(track_id)
    
    def set_violation(self, track_id, violation_type):
        """Record a violation for a track"""
        if track_id not in self.violations:
            self.violations[track_id] = {
                'type': violation_type,
                'detected_at': time.time()
            }
    
    def get_all_violations(self):
        """Get all active violations {track_id: violation_type}"""
        return {tid: v['type'] for tid, v in self.violations.items()}
