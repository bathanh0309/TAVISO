# TAVISO - Hệ Thống Giám Sát Giao Thông Đà Nẵng

Hệ thống nhận diện biển số xe thời gian thực sử dụng **YOLOv11** và **EasyOCR**, được thiết kế để triển khai giám sát lưu lượng giao thông tại Đà Nẵng.

![TAVISO Dashboard](https://img.shields.io/badge/Status-Active-success)
![Python](https://img.shields.io/badge/Python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)

## Tính năng

- **Live Streaming**: Xem camera stream real-time với detection overlay
- **AI Detection**: Nhận diện biển số xe Việt Nam bằng YOLOv11 + EasyOCR
- **Data Logging**: Tự động lưu vào SQLite database và CSV file
- **Thống kê Real-time**: Dashboard hiển thị số liệu theo giờ, ngày
- **Giao diện hiện đại**: Dark theme, glassmorphism, responsive design
- **Tiếng Việt hoàn toàn**: Phù hợp triển khai Đà Nẵng

## Giao diện

Giao diện hiện đại với dark theme, glassmorphism và Vietnamese localization:

- **Webcam stream lớn** chiếm trung tâm với real-time detection
- **Bảng theo dõi realtime** hiển thị phát hiện gần nhất
- **Bảng lịch sử** với pagination để xem dữ liệu cũ
- **Thống kê tức thời** về tổng số xe, biển số duy nhất

## Khởi động nhanh

### Yêu cầu

- Python 3.10+
- pip
- Windows 10/11

### Bước 1: Cài đặt

```powershell
# Clone repository
git clone https://github.com/bathanh0309/TAVISO.git
cd TAVISO

# Tạo virtual environment
python -m venv .venv

# Kích hoạt virtual environment
.venv\Scripts\activate

# Cài đặt PyTorch CPU (quan trọng!)
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Cài đặt các dependencies còn lại
pip install -r requirements.txt
```

### Bước 2: Chạy hệ thống

**Cách 1: Sử dụng script tự động (Khuyến nghị)**

```powershell
.\\run.bat
```

**Cách 2: Chạy thủ công**

```powershell
# Kích hoạt virtual environment trước
.venv\Scripts\activate

# Chạy server
python -m backend.main
```

### Bước 3: Truy cập Dashboard

Mở trình duyệt và truy cập:
```
http://localhost:8000
```

🎉 **Xong!** Hệ thống đã sẵn sàng hoạt động!

## Cấu trúc thư mục

```
TAVISO/
├── backend/              # FastAPI backend server
│   ├── main.py          # Application chính
│   ├── models.py        # Database models (SQLAlchemy)
│   ├── schemas.py       # Pydantic schemas
│   ├── database.py      # Database configuration
│   └── services/        # Business logic
│       ├── camera.py    # Camera stream handler
│       ├── detector.py  # YOLO + OCR detection
│       └── logger.py    # Database logging
│
├── frontend/            # HTML/CSS/JS dashboard (static)
│   ├── index.html       # Main dashboard page
│   └── static/
│       ├── css/         # Stylesheets (dark theme)
│       └── js/          # JavaScript (API integration)
│
├── config/              # Configuration files
│   └── settings.yaml    # System settings
│
├── data/                # Data storage (gitignored)
│   ├── database/        # SQLite database
│   ├── csv/             # CSV export logs
│   ├── crops/           # License plate crops
│   └── mock_stream/     # Mock camera data for testing
│
├── models/              # YOLO models (gitignored, auto-downloaded)
├── drawio/              # System architecture diagrams
├── run.sh               # Linux/macOS startup script
├── run.bat              # Windows startup script
└── requirements.txt     # Python dependencies
```

## Cấu hình

Chỉnh sửa `config/settings.yaml`:

```yaml
camera:
  source: "mock"  # Đổi thành RTSP URL khi có camera thật
  # source: "rtsp://username:password@192.168.1.100:554/stream"
  fps: 10

model:
  yolo_path: "models/yolo11n.pt"
  confidence: 0.5
  ocr_languages: ['en', 'vi']

server:
  host: "0.0.0.0"
  port: 8000
```

## Kết nối Camera IP

Để sử dụng camera thật, cập nhật `source` trong `config/settings.yaml`:

```yaml
camera:
  source: "rtsp://admin:password@192.168.1.100:554/stream1"
```

Các format hỗ trợ:
- **RTSP**: `rtsp://username:password@ip:port/path`
- **HTTP/HTTPS**: `http://ip:port/video`
- **USB Camera**: `0` (device index)
- **Video file**: `/path/to/video.mp4`

## API Endpoints

| Endpoint | Method | Mô tả |
|----------|--------|-------|
| `/` | GET | Dashboard UI |
| `/stream` | GET | Video stream (MJPEG) |
| `/api/plates` | GET | Danh sách biển số đã detect (paginated) |
| `/api/stats` | GET | Thống kê real-time |
| `/api/detect` | POST | Trigger detection thủ công |
| `/health` | GET | Health check |

## Xử lý lỗi

### Port 8000 đã được sử dụng
```yaml
# Đổi port trong config/settings.yaml
server:
  port: 8080
```

### EasyOCR không tải được model
```bash
# Đảm bảo có kết nối internet
# EasyOCR sẽ tự động download models lần đầu (~100MB)
```

### YOLO model không tìm thấy
```bash
# Model sẽ tự động download khi chạy lần đầu
# Hoặc download thủ công:
mkdir -p models
wget https://github.com/ultralytics/assets/releases/download/v8.4.0/yolo11n.pt -O models/yolo11n.pt
```

### Virtual environment lỗi
```bash
# Xóa và tạo lại
rm -rf .venv
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## License

MIT License - Xem file [LICENSE](LICENSE) để biết thêm chi tiết

## Đóng góp

Pull requests luôn được chào đón! Vui lòng:

1. Fork repository
2. Tạo feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to branch (`git push origin feature/AmazingFeature`)
5. Mở Pull Request

## Liên hệ

**Bathanh0309** - [GitHub](https://github.com/bathanh0309)

**Project Link**: [https://github.com/bathanh0309/TAVISO](https://github.com/bathanh0309/TAVISO)

---

<div align="center">

Made with ❤️ for Da Nang Traffic Monitoring

**Hệ thống giám sát giao thông thông minh cho Đà Nẵng**

</div>
