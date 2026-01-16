"""
Camera stream handler - Robust Threaded Implementation
Optimized for performance and Windows compatibility (DirectShow)
"""
import cv2
import numpy as np
import yaml
import os
import time
import threading
from pathlib import Path

class CameraStream:
    """
    Robust CameraStream class with:
    - Threaded capture (Non-blocking)
    - Auto-reconnect
    - Thread-safe locking
    - Error handling
    """
    
    def __init__(self, config_path='config/settings.yaml'):
        self.lock = threading.Lock()
        
        # Load config
        try:
            with open(config_path, 'r') as f:
                self.config = yaml.safe_load(f)
            camera_config = self.config['camera']
            self.source = camera_config['source']
            self.fps = camera_config.get('fps', 30)
            self.width = camera_config.get('width', 640)
            self.height = camera_config.get('height', 480)
        except Exception as e:
            print(f"[ERROR] Config load failed: {e}")
            self.source = 0
            self.fps = 30
            self.width = 640
            self.height = 480
        
        # State variables
        self.cap = None
        self.frame = None
        self.running = False
        self.retry_interval = 5  # seconds
        self.last_retry_time = 0
        
        # Mock variables
        self.mock_images = []
        self.mock_index = 0
        
        # Pre-allocate blank error frame
        self._create_error_frame("Initializing...")
        
        # Initialize
        self._initialize_source()
        
    def _create_error_frame(self, message):
        """Create a default frame with error message"""
        try:
            self.default_frame = np.zeros((self.height, self.width, 3), dtype=np.uint8)
            # Gray text
            cv2.putText(self.default_frame, message, (50, self.height // 2), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2)
            # Add Timestamp
            ts = time.strftime("%H:%M:%S")
            cv2.putText(self.default_frame, ts, (10, 30), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 1)
        except:
            self.default_frame = np.zeros((480, 640, 3), dtype=np.uint8)

    def _initialize_source(self):
        """Initialize camera source based on configuration"""
        
        # 1. Handle Mock
        if self.source == "mock":
             self._setup_mock()
             return

        # 2. Handle Real Camera / File
        self.running = True
        self.thread = threading.Thread(target=self._capture_loop, daemon=True)
        self.thread.start()
        print("✓ Camera capture thread started")

    def _setup_mock(self):
        """Setup mock image sequence"""
        try:
            mock_dir = self.config['camera'].get('mock_images_dir', 'data/mock_stream/images')
            if os.path.exists(mock_dir):
                files = sorted(list(Path(mock_dir).glob('*.jpg')) + list(Path(mock_dir).glob('*.png')))
                self.mock_images = [str(f) for f in files]
                if self.mock_images:
                    print(f"✓ Loaded {len(self.mock_images)} mock images")
                    # Start mock thread
                    self.running = True
                    self.thread = threading.Thread(target=self._mock_loop, daemon=True)
                    self.thread.start()
                    return
        except Exception as e:
            print(f"Mock setup failed: {e}")
        
        self._create_error_frame("Mock Data Not Found")
        
    def _mock_loop(self):
        """Loop for mock images"""
        while self.running:
            if not self.mock_images:
                time.sleep(1)
                continue
                
            img_path = self.mock_images[self.mock_index]
            frame = cv2.imread(img_path)
            
            if frame is not None:
                frame = cv2.resize(frame, (self.width, self.height))
                with self.lock:
                    self.frame = frame
            
            self.mock_index = (self.mock_index + 1) % len(self.mock_images)
            time.sleep(1.0 / self.fps)

    def _connect_camera(self):
        """Attempt to connect to camera"""
        print(f"Connecting to camera source: {self.source}...")
        
        # Handle index
        src = self.source
        if isinstance(src, str) and src.isdigit():
            src = int(src)
            
        # Initialize VideoCapture with CAP_DSHOW for Windows
        if isinstance(src, int):
             cap = cv2.VideoCapture(src, cv2.CAP_DSHOW)
        else:
             cap = cv2.VideoCapture(src) # File or IP stream
             
        if cap.isOpened():
            # Optimize for latency
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, self.fps)
            
            # Warm up
            for _ in range(3):
                cap.read()
                
            print(f"✓ Camera connected: {self.source}")
            return cap
        else:
            print(f"✗ Failed to connect to {self.source}")
            return None

    def _capture_loop(self):
        """Main thread loop for capturing frames"""
        while self.running:
            # 1. Connect if needed
            if self.cap is None or not self.cap.isOpened():
                current_time = time.time()
                if current_time - self.last_retry_time >= self.retry_interval:
                    self.cap = self._connect_camera()
                    self.last_retry_time = current_time
                
                if self.cap is None:
                    self._create_error_frame("Connecting...")
                    with self.lock:
                        self.frame = self.default_frame.copy()
                    time.sleep(0.5)
                    continue

            # 2. Read Frame
            try:
                ret, frame = self.cap.read()
                
                if ret:
                    if frame is not None and frame.size > 0:
                        # Success reading
                        with self.lock:
                            self.frame = frame
                    else:
                        print("Warning: Empty frame received")
                else:
                    # Read failed
                    print("Warning: Failed to grab frame. Reconnecting...")
                    self.cap.release()
                    self.cap = None
                    # Loop video files if needed
                    if not isinstance(self.source, int) and os.path.exists(str(self.source)):
                        # It's a file, just restart immediately
                        self.last_retry_time = 0 
                    
            except Exception as e:
                print(f"Capture error: {e}")
                if self.cap:
                    self.cap.release()
                self.cap = None
                
            # Limit loop speed slightly to prevent CPU hogging if camera is fast
            time.sleep(0.001)

    def get_frame(self):
        """Get the latest frame (Non-blocking)"""
        with self.lock:
            if self.frame is not None:
                return self.frame.copy()
            return self.default_frame.copy()
            
    def release(self):
        """Stop thread and release resources"""
        print("Releasing camera resources...")
        self.running = False
        if hasattr(self, 'thread') and self.thread.is_alive():
            self.thread.join(timeout=1.0)
            
        if self.cap is not None:
            self.cap.release()
            
    def __del__(self):
        self.release()
