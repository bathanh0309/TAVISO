"""
FastAPI main application for License Plate Recognition System
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import cv2
import yaml
import os
import asyncio

from backend.database import get_db, init_db
from backend.models import LicensePlate
from backend.schemas import LicensePlateResponse, StatsResponse
from backend.services.camera import CameraStream
from backend.services.detector import LicensePlateDetector
from backend.services.logger import DetectionLogger

# Load configuration
with open('config/settings.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize FastAPI app
app = FastAPI(
    title="License Plate Recognition System",
    description="Real-time license plate detection and tracking",
    version="1.0.0"
)

# Initialize database
init_db()

# Initialize services (lazy loading)
camera = None
detector = None
logger = None

def get_services():
    """Initialize services on first request"""
    global camera, detector, logger
    
    if camera is None:
        camera = CameraStream()
    if detector is None:
        detector = LicensePlateDetector()
    if logger is None:
        logger = DetectionLogger()
    
    return camera, detector, logger


# Mount static files
app.mount("/static", StaticFiles(directory="frontend/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve frontend HTML"""
    html_path = "frontend/index.html"
    if os.path.exists(html_path):
        with open(html_path, 'r', encoding='utf-8') as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse("<h1>Frontend not found</h1>", status_code=404)


def generate_frames():
    """Generate video frames with license plate detection"""
    cam, det, log = get_services()
    
    while True:
        frame = cam.get_frame()
        
        if frame is None:
            break
        
        # Detect license plates
        detections = det.detect_plates(frame)
        
        # Draw detections
        annotated_frame = det.draw_detections(frame, detections)
        
        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', annotated_frame)
        
        if not ret:
            continue
        
        frame_bytes = buffer.tobytes()
        
        # Yield frame in multipart format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Small delay to control FPS
        import time
        time.sleep(1.0 / config['camera']['fps'])


@app.get("/stream")
async def video_stream():
    """Video streaming endpoint"""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


@app.get("/api/plates", response_model=list[LicensePlateResponse])
async def get_plates(
    limit: int = 100,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get list of detected license plates"""
    plates = db.query(LicensePlate)\
        .order_by(LicensePlate.timestamp.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()
    
    return [plate.to_dict() for plate in plates]


@app.get("/api/stats", response_model=StatsResponse)
async def get_stats(db: Session = Depends(get_db)):
    """Get real-time statistics"""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    
    # Total detections
    total = db.query(func.count(LicensePlate.id)).scalar()
    
    # Today's detections
    today = db.query(func.count(LicensePlate.id))\
        .filter(LicensePlate.timestamp >= today_start)\
        .scalar()
    
    # This hour's detections
    this_hour = db.query(func.count(LicensePlate.id))\
        .filter(LicensePlate.timestamp >= hour_start)\
        .scalar()
    
    # Last detection
    last = db.query(LicensePlate)\
        .order_by(LicensePlate.timestamp.desc())\
        .first()
    
    # Unique plates
    unique = db.query(func.count(func.distinct(LicensePlate.plate_number))).scalar()
    
    return {
        "total_detections": total or 0,
        "today_detections": today or 0,
        "this_hour_detections": this_hour or 0,
        "last_detection": last.timestamp if last else None,
        "unique_plates": unique or 0
    }


@app.post("/api/detect")
async def manual_detect(db: Session = Depends(get_db)):
    """Manually trigger detection on current frame"""
    cam, det, log = get_services()
    
    frame = cam.get_frame()
    if frame is None:
        raise HTTPException(status_code=500, detail="Failed to get frame")
    
    detections = det.detect_plates(frame)
    
    results = []
    for detection in detections:
        # Log to database
        record = log.log_detection(
            db,
            detection['plate_number'],
            detection['confidence'],
            detection.get('crop')
        )
        
        if record:
            results.append(record.to_dict())
    
    return {"detections": len(results), "plates": results}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "services": {
            "camera": camera is not None,
            "detector": detector is not None,
            "logger": logger is not None
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "backend.main:app",
        host=config['server']['host'],
        port=config['server']['port'],
        reload=config['server']['reload']
    )
