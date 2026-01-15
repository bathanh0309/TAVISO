"""
Object tracking service using DeepSORT
"""
from deep_sort_realtime.deepsort_tracker import DeepSort
import numpy as np

class VehicleTracker:
    """
    Track vehicles across frames using DeepSORT
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
        self.tracks = {}  # History of tracks {track_id: [centroids]}
        print("✓ Tracker initialized")

    def update(self, detections, frame):
        """
        Update tracks with new detections
        
        Args:
            detections: List of dicts from detector [{bbox: [x1,y1,x2,y2], confidence: float, class_id: int}]
            frame: Current video frame
            
        Returns:
            list: List of active tracks
        """
        # Format for DeepSORT: [[left, top, w, h], confidence, detection_class]
        bbs = []
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            w = x2 - x1
            h = y2 - y1
            conf = det['confidence']
            bbs.append([[x1, y1, w, h], conf, 0])  # Class 0 for vehicle
            
        # Update tracker
        tracks = self.tracker.update_tracks(bbs, frame=frame)
        
        results = []
        for track in tracks:
            if not track.is_confirmed():
                continue
                
            track_id = track.track_id
            ltrb = track.to_ltrb()  # [left, top, right, bottom]
            
            # Store history for trajectory analysis
            center_x = int((ltrb[0] + ltrb[2]) / 2)
            center_y = int((ltrb[1] + ltrb[3]) / 2)
            
            if track_id not in self.tracks:
                self.tracks[track_id] = []
            self.tracks[track_id].append((center_x, center_y))
            
            # Keep only last 50 points
            if len(self.tracks[track_id]) > 50:
                self.tracks[track_id].pop(0)
                
            results.append({
                'track_id': track_id,
                'bbox': [int(x) for x in ltrb],
                'history': self.tracks[track_id]
            })
            
        return results

    def check_wrong_way(self, track_id, direction="down"):
        """
        Check if vehicle is moving in wrong direction
        
        Args:
            track_id: ID of the track to check
            direction: Expected valid direction ("down", "up", "left", "right")
            
        Returns:
            bool: True if wrong way
        """
        if track_id not in self.tracks or len(self.tracks[track_id]) < 10:
            return False
            
        points = self.tracks[track_id]
        start = points[0]
        end = points[-1]
        
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        
        # Threshold for movement (pixels)
        if abs(dx) < 20 and abs(dy) < 20:
            return False
            
        if direction == "down":
            return dy < -20  # Moving up is wrong
        elif direction == "up":
            return dy > 20   # Moving down is wrong
            
        return False
