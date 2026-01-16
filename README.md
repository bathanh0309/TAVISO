# TAVISO - Hệ Thống Phát Hiện Vi Phạm Giao Thông

> **Hệ thống AI giám sát giao thông thông minh** - Phát hiện vi phạm tự động bằng YOLOv11, DeepSORT và PaddleOCR

![TAVISO Dashboard](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)

## Demo

![TAVISO System Demo](data/images/result.png)

*Hệ thống đang hoạt động: Phát hiện xe máy, nhận diện biển số, và ghi nhận vi phạm real-time*

---

### Các Tính Năng Chính

| Tính Năng | Mô Tả | Công Nghệ |
|-----------|-------|-----------|
| 🚗 **Phát hiện phương tiện** | Nhận diện xe máy, ô tô, xe tải real-time | YOLOv11 |
| 🔍 **Theo dõi đối tượng** | Tracking xe qua nhiều frame | DeepSORT |
| 🔢 **Nhận diện biển số** | OCR biển số xe Việt Nam | PaddleOCR |
| ⚠️ **Phát hiện vi phạm** | Vượt tốc độ, đi ngược chiều, vượt vạch | Computer Vision |
| 💾 **Lưu trữ dữ liệu** | Tự động lưu vào SQLite + CSV | SQLAlchemy |
| 📊 **Dashboard real-time** | Giao diện web hiện đại, thống kê trực tiếp | FastAPI + HTML/CSS/JS |

### 🚨 Các Loại Vi Phạm Được Phát Hiện

| Vi Phạm | Cách Phát Hiện |
|---------|----------------|
| **Vượt tốc độ** | Tính vận tốc qua khoảng cách di chuyển giữa các frame |
| **Đi ngược chiều** | Phân tích hướng di chuyển của xe |
| **Vượt vạch liền** | Kiểm tra xe cắt qua vùng cấm |

---

##  Cài Đặt & Chạy Nhanh

### Yêu Cầu Hệ Thống

- **Python**: 3.10+
- **OS**: Windows 10/11
- **Camera**: Webcam / IP Camera / Video file

### Bước 1: Cài Đặt

```powershell
# Clone repository
git clone https://github.com/bathanh0309/TAVISO.git
cd TAVISO

# Tạo môi trường ảo
python -m venv .venv
.venv\Scripts\activate

# Cài đặt PyTorch (CPU)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Cài đặt dependencies
pip install -r requirements.txt
```

### Bước 2: Chạy Hệ Thống

```powershell
# Cách nhanh nhất
.\run.bat

# Hoặc chạy thủ công
python -m backend.main
```

### Bước 3: Mở Dashboard

Truy cập: **http://localhost:8000**

🎉 **Hoàn tất!** Hệ thống đã sẵn sàng phát hiện vi phạm!

---

## 📁 Cấu Trúc Dự Án

```
TAVISO/
├── backend/
│   ├── main.py              # FastAPI server chính
│   ├── services/
│   │   ├── detector.py      # YOLOv11 + PaddleOCR
│   │   ├── tracker.py       # DeepSORT tracking
│   │   └── camera.py        # Camera stream handler
│   └── database.py          # SQLite database
│
├── frontend/
│   ├── index.html           # Dashboard UI
│   └── static/              # CSS/JS
│
├── config/
│   └── settings.yaml        # Cấu hình hệ thống
│
├── data/
│   ├── database/            # SQLite files
│   ├── csv/                 # CSV logs
│   └── images/              # Screenshots
│
└── models/                  # YOLO models (auto-download)
```

---

## ⚙️ Cấu Hình

Chỉnh sửa `config/settings.yaml`:

```yaml
camera:
  source: "mock"  # Hoặc: 0 (webcam), rtsp://..., video.mp4
  fps: 10

model:
  yolo_path: "models/yolo11n.pt"
  confidence: 0.5

violations:
  speed_limit: 50  # km/h
  line_crossing_enabled: true
```

### Kết Nối Camera IP

```yaml
camera:
  source: "rtsp://admin:password@192.168.1.100:554/stream"
```

---

## 🔌 API Endpoints

| Endpoint | Method | Chức Năng |
|----------|--------|-----------|
| `/` | GET | Dashboard UI |
| `/stream` | GET | Video stream (MJPEG) |
| `/api/violations` | GET | Danh sách vi phạm (có phân trang) |
| `/api/stats` | GET | Thống kê real-time |
| `/health` | GET | Kiểm tra trạng thái |

---

## 🛠️ Công Nghệ Sử Dụng

| Thành Phần | Công Nghệ |
|------------|-----------|
| **Object Detection** | YOLOv11 (Ultralytics) |
| **Object Tracking** | DeepSORT |
| **OCR** | PaddleOCR |
| **Backend** | FastAPI + SQLAlchemy |
| **Frontend** | HTML5 + CSS3 + Vanilla JS |
| **Database** | SQLite |
| **Computer Vision** | OpenCV |

---

## 📊 Dữ Liệu Đầu Ra

Hệ thống tự động lưu:

1. **SQLite Database** (`data/database/violations.db`)
   - Bảng violations: ID, Ngày giờ, Biển số, Loại vi phạm, Tọa độ
   
2. **CSV Files** (`data/csv/violations_YYYYMMDD.csv`)
   - Format: timestamp, plate_number, violation_type, location

3. **Ảnh chụp** (`data/images/`)
   - Ảnh biển số đã crop
   - Screenshots vi phạm

---

