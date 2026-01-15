"""
Vehicle and license plate detector using YOLO and PaddleOCR
"""
from ultralytics import YOLO
from paddleocr import PaddleOCR
import cv2
import numpy as np
import yaml
import os
import re

class LicensePlateDetector:
    """Detect vehicles and read license plates from images"""
    
    # COCO class IDs for vehicles
    VEHICLE_CLASSES = {
        2: 'car',
        3: 'motorcycle', 
        5: 'bus',
        7: 'truck'
    }
    
    def __init__(self, config_path='config/settings.yaml'):
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Load YOLO model
        model_path = self.config['model']['yolo_path']
        print(f"Loading YOLO model from {model_path}...")
        self.yolo = YOLO(model_path)
        
        # Initialize PaddleOCR
        print("Initializing PaddleOCR...")
        ocr_config = self.config.get('ocr', {})
        self.ocr = PaddleOCR(
            use_angle_cls=ocr_config.get('use_angle_cls', True),
            lang=ocr_config.get('lang', 'en')
        )
        
        self.confidence_threshold = self.config['model']['confidence']
        self.vehicle_classes = self.config['model'].get('vehicle_classes', [2, 3, 5, 7])
        self.min_plate_area = self.config['detection'].get('min_plate_area', 100)
        
        print("✓ Detector initialized successfully!")
    
    def detect_vehicles(self, frame):
        """
        Detect vehicles in a frame
        
        Args:
            frame: OpenCV image (numpy array)
        
        Returns:
            list: List of detections [{bbox, confidence, class_id, class_name}]
        """
        detections = []
        
        # Run YOLO detection
        results = self.yolo(frame, verbose=False)
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Get class ID
                class_id = int(box.cls[0])
                
                # Filter for vehicles only
                if class_id not in self.vehicle_classes:
                    continue
                
                # Get confidence
                conf = float(box.conf[0])
                
                if conf < self.confidence_threshold:
                    continue
                
                # Get bounding box
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                
                detections.append({
                    'bbox': (x1, y1, x2, y2),
                    'confidence': conf,
                    'class_id': class_id,
                    'class_name': self.VEHICLE_CLASSES.get(class_id, 'vehicle')
                })
        
        return detections
    
    def detect_plates(self, frame):
        """
        Detect license plates in a frame (legacy method for compatibility)
        
        Args:
            frame: OpenCV image (numpy array)
        
        Returns:
            list: List of detections [{plate_number, confidence, bbox}]
        """
        detections = []
        
        # Run YOLO detection for all objects
        results = self.yolo(frame, verbose=False)
        
        for r in results:
            boxes = r.boxes
            for box in boxes:
                # Get confidence
                conf = float(box.conf[0])
                
                if conf < self.confidence_threshold:
                    continue
                
                # Get bounding box
                x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().astype(int)
                
                # Check minimum area
                area = (x2 - x1) * (y2 - y1)
                if area < self.min_plate_area:
                    continue
                
                # Crop the plate region
                plate_crop = frame[y1:y2, x1:x2]
                
                # Read text with OCR
                plate_number = self._read_plate_text(plate_crop)
                
                if plate_number:
                    detections.append({
                        'plate_number': plate_number,
                        'confidence': conf,
                        'bbox': (x1, y1, x2, y2),
                        'crop': plate_crop
                    })
        
        return detections

    def read_plate_from_vehicle(self, frame, vehicle_bbox):
        """
        Try to read license plate from a detected vehicle region
        
        Args:
            frame: Full frame
            vehicle_bbox: Vehicle bounding box (x1, y1, x2, y2)
        
        Returns:
            str: License plate number or None
        """
        x1, y1, x2, y2 = vehicle_bbox
        
        # Expand region slightly to capture plate
        h, w = frame.shape[:2]
        pad_x = int((x2 - x1) * 0.1)
        pad_y = int((y2 - y1) * 0.2)
        
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)
        
        # Focus on lower portion of vehicle (where plate usually is)
        plate_region_y1 = y1 + int((y2 - y1) * 0.5)  # Lower 50%
        vehicle_crop = frame[plate_region_y1:y2, x1:x2]
        
        if vehicle_crop.size == 0:
            return None
        
        return self._read_plate_text(vehicle_crop)
    
    def _read_plate_text(self, plate_image):
        """
        Extract text from license plate crop using PaddleOCR
        
        Args:
            plate_image: Cropped plate image
        
        Returns:
            str: Detected plate number or None
        """
        try:
            if plate_image is None or plate_image.size == 0:
                return None
            
            # Run PaddleOCR
            results = self.ocr.ocr(plate_image, cls=True)
            
            if not results or not results[0]:
                return None
            
            # Combine all detected text
            texts = []
            for line in results[0]:
                if line and len(line) >= 2:
                    text = line[1][0]  # Get text content
                    texts.append(text)
            
            if not texts:
                return None
            
            # Combine and clean text
            combined = ' '.join(texts)
            
            # Clean up text (keep alphanumeric and Vietnamese plate format)
            # Vietnamese plates: XX-XXXXX or XXX-XXX.XX
            plate_text = re.sub(r'[^A-Z0-9\-\.]', '', combined.upper())
            
            # Minimum length check
            if len(plate_text) < 5:
                return None
            
            return plate_text
            
        except Exception as e:
            print(f"OCR error: {e}")
            return None
    
    def draw_detections(self, frame, detections, violation_info=None):
        """
        Draw bounding boxes and labels on frame
        
        Args:
            frame: Original frame
            detections: List of vehicle detections
            violation_info: Optional dict of {track_id: violation_type}
        
        Returns:
            frame: Annotated frame
        """
        annotated = frame.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            conf = det['confidence']
            class_name = det.get('class_name', 'vehicle')
            track_id = det.get('track_id')
            plate = det.get('plate_number', '')
            
            # Check if this track has a violation
            is_violation = False
            violation_type = None
            if violation_info and track_id and track_id in violation_info:
                is_violation = True
                violation_type = violation_info[track_id]
            
            # Colors: Green for normal, Red for violation
            color = (0, 0, 255) if is_violation else (0, 255, 0)
            
            # Draw rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), color, 2)
            
            # Build label
            label_parts = [class_name]
            if track_id:
                label_parts.append(f"ID:{track_id}")
            if plate:
                label_parts.append(plate)
            if is_violation:
                vtype_vi = {
                    "wrong_way": "Ngược chiều",
                    "speeding": "Quá tốc độ",
                    "line_crossing": "Vượt vạch"
                }.get(violation_type, violation_type)
                label_parts.append(f"⚠️{vtype_vi}")
            
            label = " | ".join(label_parts)
            
            # Draw label background
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 2)
            cv2.rectangle(annotated, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0] + 10, y1), color, -1)
            cv2.putText(annotated, label, (x1 + 5, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)
        
        return annotated
