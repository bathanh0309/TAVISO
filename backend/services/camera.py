"""
Camera stream handler - supports webcam, IP cameras, and mock streams
"""
import cv2
import numpy as np
import yaml
import os
import time
from pathlib import Path

import threading

class CameraStream:
    """Handle camera streaming from various sources"""
    
    def __init__(self, config_path='config/settings.yaml'):
        self.lock = threading.Lock()
        # Load config
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        camera_config = self.config['camera']
        self.source = camera_config['source']
        self.fps = camera_config.get('fps', 15)
        self.width = camera_config.get('width', 1280)
        self.height = camera_config.get('height', 720)
        
        self.cap = None
        self.frame = None  # Current frame buffer
        self.running = False
        self.thread = None
        
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
            # Reverting to CAP_DSHOW because MSMF is failing with error -1072875772
            self.cap = cv2.VideoCapture(device_index, cv2.CAP_DSHOW)
            
            if self.cap.isOpened():
                # Force 640x480 for stability
                self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                self.cap.set(cv2.CAP_PROP_FPS, 30)
                
                # Warm up
                for _ in range(5):
                    self.cap.read()
                
                actual_width = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                actual_height = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                print(f"✓ Webcam opened: {actual_width}x{actual_height} (Backend: DSHOW)")
                
                # Start capture thread
                self.start()
            else:
                print(f"✗ Failed to open webcam {device_index}")
                self._create_default_frame()
                self.frame = self.default_frame.copy()
        
        elif self.source == "mock":
            # Use mock images logic (simplified for threading compatibility)
            mock_dir = self.config['camera'].get('mock_images_dir', 'data/mock_stream/images')
            if os.path.exists(mock_dir):
                image_files = list(Path(mock_dir).glob('*.jpg')) + \
                             list(Path(mock_dir).glob('*.png'))
                self.mock_images = [str(f) for f in sorted(image_files)]
                if self.mock_images:
                    print(f"✓ Loaded {len(self.mock_images)} mock images")
            
            if not self.mock_images:
                self._create_default_frame()
                self.frame = self.default_frame.copy()
            else:
                # Pre-load first frame
                self.frame = cv2.imread(self.mock_images[0])
                if self.frame is None:
                    self._create_default_frame()
                    self.frame = self.default_frame.copy()

        elif self.source.startswith(('rtsp://', 'http://', 'https://')):
            # IP camera stream
            print(f"Connecting to IP camera: {self.source}")
            self.cap = cv2.VideoCapture(self.source)
            
            if self.cap.isOpened():
                print("✓ IP camera connected")
                self.start()
            else:
                print(f"✗ Failed to connect to: {self.source}")
                self._create_default_frame()
                self.frame = self.default_frame.copy()
        
        else:
            # Video file
            if os.path.exists(self.source):
                print(f"Opening video file: {self.source}")
                self.cap = cv2.VideoCapture(self.source)
                if self.cap.isOpened():
                    print("✓ Video file opened")
                    self.start()
                else:
                    self._create_default_frame()
                    self.frame = self.default_frame.copy()
            else:
                print(f"Unknown source: {self.source}")
                self._create_default_frame()
                self.frame = self.default_frame.copy()
    
    def start(self):
        """Start the thread to read frames from the video stream"""
        if self.running:
            return
        
        self.running = True
        self.thread = threading.Thread(target=self.update, daemon=True)
        self.thread.start()
        print("✓ Camera capture thread started")

    def update(self):
        """Output frames from buffer (Thread function)"""
        while self.running:
            if self.cap is None or not self.cap.isOpened():
                time.sleep(0.1)
                continue
                
            ret, frame = self.cap.read()
            
            if ret:
                # Add timestamp
                self._add_timestamp(frame)
                with self.lock:
                    self.frame = frame
            else:
                # If video file, loop
                if not isinstance(self.source, int) and self.cap.get(cv2.CAP_PROP_POS_FRAMES) == self.cap.get(cv2.CAP_PROP_FRAME_COUNT):
                     self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                else:
                     # Wait a bit if read failed
                     time.sleep(0.01)

            # Cap read speed (simple approximate)
            # time.sleep(0.005) 

    def _create_default_frame(self):
        """Create a default frame when no source is available"""
        self.default_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
        text = "Camera Not Available"
        cv2.putText(self.default_frame, text, (50, self.height // 2),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (100, 100, 100), 2)

    def get_frame(self):
        """Get the latest frame (Non-blocking)"""
        self.frame_count += 1
        
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
            elif hasattr(self, 'default_frame'):
                return self.default_frame.copy()
            else:
                return None

    def _add_timestamp(self, frame):
        """Add timestamp overlay to frame"""
        try:
            timestamp = time.strftime("%d/%m/%Y %H:%M:%S")
            cv2.putText(frame, timestamp, (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
        except:
            pass
    
    def release(self):
        """Release camera resources"""
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        if self.cap is not None:
            self.cap.release()
            self.cap = None
    
    def is_opened(self):
        return self.cap is not None and self.cap.isOpened()
    
    def __del__(self):
        self.release()
