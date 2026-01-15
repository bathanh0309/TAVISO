"""
Camera stream handler - supports IP cameras and mock streams
"""
import cv2
import numpy as np
import yaml
import os
import time
from pathlib import Path

class CameraStream:
    """Handle camera streaming from various sources"""
    
    def __init__(self, config_path='config/settings.yaml'):
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        self.source = self.config['camera']['source']
        self.fps = self.config['camera']['fps']
        self.cap = None
        self.mock_images = []
        self.mock_index = 0
        
        self._initialize_source()
    
    def _initialize_source(self):
        """Initialize camera source based on configuration"""
        if self.source == "mock":
            # Use mock images
            mock_dir = self.config['camera']['mock_images_dir']
            if os.path.exists(mock_dir):
                image_files = list(Path(mock_dir).glob('*.jpg')) + \
                             list(Path(mock_dir).glob('*.png'))
                self.mock_images = [str(f) for f in sorted(image_files)]
                
                if self.mock_images:
                    print(f"✓ Loaded {len(self.mock_images)} mock images")
                else:
                    print("⚠ No mock images found, using default")
                    self._create_default_frame()
            else:
                print("⚠ Mock directory not found, using default")
                self._create_default_frame()
        else:
            # Use real camera (RTSP, HTTP, or device index)
            print(f"Connecting to camera: {self.source}")
            self.cap = cv2.VideoCapture(self.source)
            
            if not self.cap.isOpened():
                print(f"✗ Failed to open camera: {self.source}")
                self._create_default_frame()
    
    def _create_default_frame(self):
        """Create a default frame when no source is available"""
        self.default_frame = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(self.default_frame, "No Camera Source", (180, 240),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
    
    def get_frame(self):
        """
        Get next frame from camera
        
        Returns:
            numpy.ndarray: Frame image or None if failed
        """
        if self.source == "mock":
            return self._get_mock_frame()
        else:
            return self._get_real_frame()
    
    def _get_mock_frame(self):
        """Get frame from mock images"""
        if not self.mock_images:
            return self.default_frame if hasattr(self, 'default_frame') else None
        
        # Cycle through images
        image_path = self.mock_images[self.mock_index]
        frame = cv2.imread(image_path)
        
        self.mock_index = (self.mock_index + 1) % len(self.mock_images)
        
        # Add timestamp overlay
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        cv2.putText(frame, timestamp, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        
        return frame
    
    def _get_real_frame(self):
        """Get frame from real camera"""
        if self.cap is None or not self.cap.isOpened():
            return self.default_frame if hasattr(self, 'default_frame') else None
        
        ret, frame = self.cap.read()
        
        if not ret:
            print("Failed to grab frame")
            return None
        
        return frame
    
    def release(self):
        """Release camera resources"""
        if self.cap is not None:
            self.cap.release()
    
    def __del__(self):
        """Cleanup on deletion"""
        self.release()
