"""
Camera stream handler - supports webcam, IP cameras, and mock streams
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
        
        camera_config = self.config['camera']
        self.source = camera_config['source']
        self.fps = camera_config.get('fps', 15)
        self.width = camera_config.get('width', 1280)
        self.height = camera_config.get('height', 720)
        
        self.cap = None
        self.mock_images = []
        self.mock_index = 0
        self.frame_count = 0
        
        self._initialize_source()
    
    def _initialize_source(self):
        """Initialize camera source based on configuration"""
        # Handle webcam (integer source)
        if isinstance(self.source, int) or (isinstance(self.source, str) and self.source.isdigit()):
            device_index = int(self.source)
            print(f"Opening webcam (device {device_index})...")
            self.cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)  # Use DirectShow on Windows
            
            if self.cap.isOpened():
                # Set resolution
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
                self.cap.set(cv2.CAP_PROP_FPS, self.fps)
                
                actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"✓ Webcam opened: {actual_width}x{actual_height}")
            else:
                print(f"✗ Failed to open webcam {device_index}")
                self._create_default_frame()
        
        elif self.source == "mock":
            # Use mock images
            mock_dir = self.config['camera'].get('mock_images_dir', 'data/mock_stream/images')
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
        
        elif self.source.startswith(('rtsp://', 'http://', 'https://')):
            # IP camera stream
            print(f"Connecting to IP camera: {self.source}")
            self.cap = cv2.VideoCapture(self.source)
            
            if self.cap.isOpened():
                print("✓ IP camera connected")
            else:
                print(f"✗ Failed to connect to: {self.source}")
                self._create_default_frame()
        
        else:
            # Try as video file
            if os.path.exists(self.source):
                print(f"Opening video file: {self.source}")
                self.cap = cv2.VideoCapture(self.source)
                if self.cap.isOpened():
                    print("✓ Video file opened")
                else:
                    self._create_default_frame()
            else:
                print(f"Unknown source: {self.source}")
                self._create_default_frame()
    
    def _create_default_frame(self):
        """Create a default frame when no source is available"""
        self.default_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        
        # Draw a "No Camera" message
        text = "Camera Not Available"
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 1.5
        thickness = 3
        
        text_size = cv2.getTextSize(text, font, font_scale, thickness)[0]
        text_x = (self.width - text_size[0]) // 2
        text_y = (self.height + text_size[1]) // 2
        
        cv2.putText(self.default_frame, text, (text_x, text_y),
                   font, font_scale, (100, 100, 100), thickness)
        
        # Add instruction
        instruction = "Configure camera in config/settings.yaml"
        inst_size = cv2.getTextSize(instruction, font, 0.7, 2)[0]
        cv2.putText(self.default_frame, instruction, 
                   ((self.width - inst_size[0]) // 2, text_y + 50),
                   font, 0.7, (80, 80, 80), 2)
    
    def get_frame(self):
        """
        Get next frame from camera
        
        Returns:
            numpy.ndarray: Frame image or None if failed
        """
        self.frame_count += 1
        
        if isinstance(self.source, int) or (isinstance(self.source, str) and self.source.isdigit()):
            return self._get_camera_frame()
        elif self.source == "mock":
            return self._get_mock_frame()
        elif self.cap is not None:
            return self._get_camera_frame()
        else:
            return self.default_frame if hasattr(self, 'default_frame') else None
    
    def _get_mock_frame(self):
        """Get frame from mock images"""
        if not self.mock_images:
            return self.default_frame if hasattr(self, 'default_frame') else None
        
        # Cycle through images
        image_path = self.mock_images[self.mock_index]
        frame = cv2.imread(image_path)
        
        self.mock_index = (self.mock_index + 1) % len(self.mock_images)
        
        if frame is None:
            return self.default_frame if hasattr(self, 'default_frame') else None
        
        # Resize to configured size
        frame = cv2.resize(frame, (self.width, self.height))
        
        # Add timestamp overlay
        self._add_timestamp(frame)
        
        return frame
    
    def _get_camera_frame(self):
        """Get frame from real camera or video"""
        if self.cap is None or not self.cap.isOpened():
            return self.default_frame if hasattr(self, 'default_frame') else None
        
        ret, frame = self.cap.read()
        
        if not ret:
            # For video files, loop back to start
            if not isinstance(self.source, int) and os.path.isfile(str(self.source)):
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                ret, frame = self.cap.read()
            
            if not ret:
                return self.default_frame if hasattr(self, 'default_frame') else None
        
        # Add timestamp
        self._add_timestamp(frame)
        
        return frame
    
    def _add_timestamp(self, frame):
        """Add timestamp overlay to frame"""
        timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
        cv2.putText(frame, timestamp, (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    
    def release(self):
        """Release camera resources"""
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def is_opened(self):
        """Check if camera is available"""
        if self.source == "mock":
            return len(self.mock_images) > 0 or hasattr(self, 'default_frame')
        return self.cap is not None and self.cap.isOpened()
    
    def __del__(self):
        """Cleanup on deletion"""
        self.release()
