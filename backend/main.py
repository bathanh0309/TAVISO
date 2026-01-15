"""
FastAPI main application for Traffic Violation Detection System
"""
from fastapi import FastAPI, Depends, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta
import cv2
import yaml
import os
import time

from backend.database import get_db, init_db
from backend.models import LicensePlate, TrafficViolation
from backend.schemas import (
    LicensePlateResponse, StatsResponse, 
    ViolationResponse, ViolationStatsResponse, RealtimeResponse, RealtimeViolation
)
from backend.services.camera import CameraStream
from backend.services.detector import LicensePlateDetector
from backend.services.tracker import VehicleTracker
from backend.services.violation_detector import ViolationDetector
from backend.services.logger import DetectionLogger

# Load configuration
with open('config/settings.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize FastAPI app
app = FastAPI(
    title="TAVISO - Traffic Violation Detection System",
    description="Real-time traffic violation detection using YOLOv11 + DeepSORT + PaddleOCR",
    version="2.0.0"
)

# Initialize database
init_db()

# Initialize services (lazy loading)
camera = None
detector = None
tracker = None
violation_detector = None
logger = None

def get_services():
    """Initialize services on first request"""
    global camera, detector, tracker, violation_detector, logger
    
    if camera is None:
        print("\n=== Initializing Services ===")
        camera = CameraStream()
    if detector is None:
        detector = LicensePlateDetector()
    if tracker is None:
        tracker = VehicleTracker()
    if violation_detector is None:
        violation_detector = ViolationDetector()
    if logger is None:
        logger = DetectionLogger()
        print("=== All Services Ready ===\n")
    
    return camera, detector, tracker, violation_detector, logger


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
    """Generate video frames with vehicle detection and violation tracking"""
    cam, det, trk, vio_det, log = get_services()
    
    # Get database session for logging
    from backend.database import SessionLocal
    db = SessionLocal()
    
    try:
        while True:
            frame = cam.get_frame()
            
            if frame is None:
                break
            
            # Detect vehicles
            detections = det.detect_vehicles(frame)
            
            # Update tracker
            tracks = trk.update(detections, frame)
            
            # Check for violations
            violations = vio_det.analyze_tracks(trk, det, frame, db, log)
            
            # Try to read plates for tracked vehicles
            for track in tracks:
                if not trk.get_license_plate(track['track_id']):
                    plate = det.read_plate_from_vehicle(frame, track['bbox'])
                    if plate:
                        trk.set_license_plate(track['track_id'], plate)
                        track['plate_number'] = plate
            
            # Get violation info for drawing
            violation_info = trk.get_all_violations()
            
            # Draw detections with tracking info
            annotated_frame = det.draw_detections(frame, tracks, violation_info)
            
            # Encode frame to JPEG
            ret, buffer = cv2.imencode('.jpg', annotated_frame)
            
            if not ret:
                continue
            
            frame_bytes = buffer.tobytes()
            
            # Yield frame in multipart format
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            # Control FPS
            time.sleep(1.0 / config['camera']['fps'])
    finally:
        db.close()


@app.get("/stream")
async def video_stream():
    """Video streaming endpoint"""
    return StreamingResponse(
        generate_frames(),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )


# ============== VIOLATION API ENDPOINTS ==============

@app.get("/api/violations", response_model=list[ViolationResponse])
async def get_violations(
    limit: int = 50,
    offset: int = 0,
    db: Session = Depends(get_db)
):
    """Get list of traffic violations (paginated)"""
    violations = db.query(TrafficViolation)\
        .order_by(TrafficViolation.timestamp.desc())\
        .limit(limit)\
        .offset(offset)\
        .all()
    
    return [v.to_dict() for v in violations]


@app.get("/api/violations/realtime")
async def get_realtime_violations(
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """Get latest violations for realtime display"""
    violations = db.query(TrafficViolation)\
        .order_by(TrafficViolation.timestamp.desc())\
        .limit(limit)\
        .all()
    
    realtime_list = []
    for v in violations:
        realtime_list.append({
            "id": v.id,
            "date": v.timestamp.strftime("%d/%m/%Y") if v.timestamp else "",
            "time": v.timestamp.strftime("%H:%M:%S") if v.timestamp else "",
            "license_plate": v.license_plate or "Không rõ",
            "violation_type_vi": v._get_violation_type_vi(),
            "confidence": round(v.confidence, 2)
        })
    
    total = db.query(func.count(TrafficViolation.id)).scalar() or 0
    
    return {
        "violations": realtime_list,
        "total_count": total
    }


@app.get("/api/violations/stats", response_model=ViolationStatsResponse)
async def get_violation_stats(db: Session = Depends(get_db)):
    """Get violation statistics"""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    
    # Total violations
    total = db.query(func.count(TrafficViolation.id)).scalar() or 0
    
    # Today's violations
    today = db.query(func.count(TrafficViolation.id))\
        .filter(TrafficViolation.timestamp >= today_start)\
        .scalar() or 0
    
    # This hour's violations
    this_hour = db.query(func.count(TrafficViolation.id))\
        .filter(TrafficViolation.timestamp >= hour_start)\
        .scalar() or 0
    
    # Count by type
    wrong_way = db.query(func.count(TrafficViolation.id))\
        .filter(TrafficViolation.violation_type == "wrong_way")\
        .scalar() or 0
    
    speeding = db.query(func.count(TrafficViolation.id))\
        .filter(TrafficViolation.violation_type == "speeding")\
        .scalar() or 0
    
    line_crossing = db.query(func.count(TrafficViolation.id))\
        .filter(TrafficViolation.violation_type == "line_crossing")\
        .scalar() or 0
    
    # Last violation
    last = db.query(TrafficViolation)\
        .order_by(TrafficViolation.timestamp.desc())\
        .first()
    
    return {
        "total_violations": total,
        "today_violations": today,
        "this_hour_violations": this_hour,
        "wrong_way_count": wrong_way,
        "speeding_count": speeding,
        "line_crossing_count": line_crossing,
        "last_violation": last.to_dict() if last else None
    }


# ============== LICENSE PLATE API ENDPOINTS ==============

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
    """Get license plate detection statistics"""
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    hour_start = now.replace(minute=0, second=0, microsecond=0)
    
    total = db.query(func.count(LicensePlate.id)).scalar() or 0
    today = db.query(func.count(LicensePlate.id))\
        .filter(LicensePlate.timestamp >= today_start)\
        .scalar() or 0
    this_hour = db.query(func.count(LicensePlate.id))\
        .filter(LicensePlate.timestamp >= hour_start)\
        .scalar() or 0
    last = db.query(LicensePlate)\
        .order_by(LicensePlate.timestamp.desc())\
        .first()
    unique = db.query(func.count(func.distinct(LicensePlate.plate_number))).scalar() or 0
    
    return {
        "total_detections": total,
        "today_detections": today,
        "this_hour_detections": this_hour,
        "last_detection": last.timestamp if last else None,
        "unique_plates": unique
    }


# ============== HEALTH CHECK ==============

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "2.0.0",
        "services": {
            "camera": camera is not None,
            "detector": detector is not None,
            "tracker": tracker is not None,
            "violation_detector": violation_detector is not None,
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
