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
        
        # Load YOLO model for vehicle detection
        model_path = self.config['model']['yolo_path']
        print(f"Loading Vehicle Detection YOLO from {model_path}...")
        self.yolo = YOLO(model_path)
        
        # Load YOLO model for license plate detection (optional)
        plate_config = self.config.get('license_plate', {})
        plate_model_path = plate_config.get('model_path', 'models/license_plate_detector.pt')
        
        if os.path.exists(plate_model_path):
            print(f"Loading License Plate YOLO from {plate_model_path}...")
            self.plate_yolo = YOLO(plate_model_path)
            self.plate_confidence = plate_config.get('confidence', 0.4)
            self.use_plate_yolo = True
            print("✓ License Plate YOLO model loaded!")
        else:
            self.plate_yolo = None
            self.use_plate_yolo = False
            print("⚠ No License Plate YOLO model found - using OCR only mode")
        
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
        
        # Debug logging
        if len(detections) > 0:
            print(f"[DETECTOR] Found {len(detections)} vehicles")
        
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
        Uses 2-stage approach:
        1. YOLOv11 License Plate Detection (if available) to locate plate
        2. PaddleOCR to read characters
        
        Args:
            frame: Full frame
            vehicle_bbox: Vehicle bounding box (x1, y1, x2, y2)
        
        Returns:
            str: License plate number or None
        """
        x1, y1, x2, y2 = vehicle_bbox
        
        # Expand region to capture plate
        h, w = frame.shape[:2]
        pad_x = int((x2 - x1) * 0.15)
        pad_y = int((y2 - y1) * 0.25)
        
        x1 = max(0, x1 - pad_x)
        y1 = max(0, y1 - pad_y)
        x2 = min(w, x2 + pad_x)
        y2 = min(h, y2 + pad_y)
        
        # Focus on lower portion of vehicle (where plate usually is)
        plate_region_y1 = y1 + int((y2 - y1) * 0.3)  # Bottom 70%
        vehicle_crop = frame[plate_region_y1:y2, x1:x2]
        
        if vehicle_crop.size == 0:
            return None
        
        # Method 1: Use YOLOv11 License Plate Detection (if available)
        if self.use_plate_yolo and self.plate_yolo is not None:
            try:
                # Run YOLO license plate detection on vehicle crop
                plate_results = self.plate_yolo(vehicle_crop, verbose=False)
                
                for r in plate_results:
                    boxes = r.boxes
                    if len(boxes) == 0:
                        continue
                    
                    # Get the plate with highest confidence
                    best_conf = 0
                    best_plate_crop = None
                    
                    for box in boxes:
                        conf = float(box.conf[0])
                        if conf > best_conf and conf >= self.plate_confidence:
                            px1, py1, px2, py2 = box.xyxy[0].cpu().numpy().astype(int)
                            
                            # Validate plate dimensions
                            plate_w = px2 - px1
                            plate_h = py2 - py1
                            if plate_w > 20 and plate_h > 10:  # Minimum size
                                best_conf = conf
                                best_plate_crop = vehicle_crop[py1:py2, px1:px2]
                    
                    # If found a good plate, read it with OCR
                    if best_plate_crop is not None:
                        plate_text = self._read_plate_text(best_plate_crop)
                        if plate_text:
                            print(f"[YOLO+OCR] Detected plate: {plate_text} (conf: {best_conf:.2f})")
                            return plate_text
                
            except Exception as e:
                print(f"[YOLO LP ERROR] {e}, falling back to OCR-only")
        
        # Method 2: Fallback to OCR-only (original method)
        plate_text = self._read_plate_text(vehicle_crop)
        
        if plate_text:
            print(f"[OCR] Detected plate: {plate_text}")
        
        return plate_text
    
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
            
            # Preprocessing to improve OCR accuracy
            # 1. Convert to grayscale
            if len(plate_image.shape) == 3:
                gray = cv2.cvtColor(plate_image, cv2.COLOR_BGR2GRAY)
            else:
                gray = plate_image
            
            # 2. Increase contrast using CLAHE
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
            enhanced = clahe.apply(gray)
            
            # 3. Denoise
            denoised = cv2.fastNlMeansDenoising(enhanced, None, 10, 7, 21)
            
            # 4. Resize if too small (OCR works better on larger images)
            h, w = denoised.shape[:2]
            if h < 50:
                scale = 50 / h
                new_w = int(w * scale)
                denoised = cv2.resize(denoised, (new_w, 50), interpolation=cv2.INTER_CUBIC)
            
            # Run PaddleOCR on both original and preprocessed
            results_original = self.ocr.ocr(plate_image, cls=True)
            results_enhanced = self.ocr.ocr(denoised, cls=True)
            
            # Try both results
            all_results = []
            if results_original and results_original[0]:
                all_results.extend(results_original[0])
            if results_enhanced and results_enhanced[0]:
                all_results.extend(results_enhanced[0])
            
            if not all_results:
                return None
            
            # Combine all detected text
            texts = []
            for line in all_results:
                if line and len(line) >= 2:
                    text = line[1][0]  # Get text content
                    confidence = line[1][1]  # Get confidence
                    if confidence > 0.5:  # Only use high confidence results
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
            print(f"[OCR ERROR] {e}")
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
            conf = det.get('confidence', 0.5)  # Safe access with default
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
