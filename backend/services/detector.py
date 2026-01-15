"""
License plate detector using YOLO and OCR
"""
from ultralytics import YOLO
import easyocr
import cv2
import numpy as np
import yaml
import os
import re

class LicensePlateDetector:
    """Detect and read license plates from images"""
    
    def __init__(self, config_path='config/settings.yaml'):
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Load YOLO model
        model_path = self.config['model']['yolo_path']
        print(f"Loading YOLO model from {model_path}...")
        self.yolo = YOLO(model_path)
        
        # Initialize OCR reader
        print("Initializing EasyOCR...")
        self.reader = easyocr.Reader(
            self.config['model']['ocr_languages'],
            gpu=False  # Set to True if you have GPU
        )
        
        self.confidence_threshold = self.config['model']['confidence']
        self.min_plate_area = self.config['detection']['min_plate_area']
        
        print("✓ Detector initialized successfully!")
    
    def detect_plates(self, frame):
        """
        Detect license plates in a frame
        
        Args:
            frame: OpenCV image (numpy array)
        
        Returns:
            list: List of detections [{plate_number, confidence, bbox}]
        """
        detections = []
        
        # Run YOLO detection
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
    
    def _read_plate_text(self, plate_image):
        """
        Extract text from license plate crop using OCR
        
        Args:
            plate_image: Cropped plate image
        
        Returns:
            str: Detected plate number or None
        """
        try:
            # Preprocess image for better OCR
            gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
            _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
            
            # Run OCR
            results = self.reader.readtext(binary)
            
            if not results:
                return None
            
            # Combine all detected text
            text = ' '.join([result[1] for result in results])
            
            # Clean up text (remove special characters, keep alphanumeric)
            plate_text = re.sub(r'[^A-Z0-9]', '', text.upper())
            
            return plate_text if plate_text else None
            
        except Exception as e:
            print(f"OCR error: {e}")
            return None
    
    def draw_detections(self, frame, detections):
        """
        Draw bounding boxes and labels on frame
        
        Args:
            frame: Original frame
            detections: List of detections
        
        Returns:
            frame: Annotated frame
        """
        annotated = frame.copy()
        
        for det in detections:
            x1, y1, x2, y2 = det['bbox']
            plate = det['plate_number']
            conf = det['confidence']
            
            # Draw rectangle
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 255, 0), 2)
            
            # Draw label
            label = f"{plate} ({conf:.2%})"
            label_size, _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
            cv2.rectangle(annotated, (x1, y1 - label_size[1] - 10), 
                         (x1 + label_size[0], y1), (0, 255, 0), -1)
            cv2.putText(annotated, label, (x1, y1 - 5), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
        
        return annotated
