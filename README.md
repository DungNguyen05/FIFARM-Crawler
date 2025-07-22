# Article Crawler

Flexible web crawler để crawl bài viết từ Coin98.net với khả năng cấu hình thời gian chạy linh hoạt qua file `.env`.

## Yêu cầu hệ thống

- Python 3.8+
- Internet connection
- API endpoint để gửi dữ liệu

## 🔧 Cài đặt và thiết lập

### Bước 1: Tạo virtual environment

```bash
# Tạo virtual environment
python -m venv venv

# Kích hoạt virtual environment
# Trên Windows:
venv\Scripts\activate

# Trên macOS/Linux:
source venv/bin/activate
```

### Bước 2: Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### Bước 3: Cấu hình môi trường

```bash
# Copy file example thành file .env
cp .env.example .env

# Chỉnh sửa file .env
nano .env
# hoặc dùng editor khác: code .env, vim .env, etc.
```

## ⚙️ Cấu hình thời gian chạy

Mở file `.env` và chỉnh sửa các thông số:

### 🕐 Các tùy chọn thời gian

#### 1. Chạy theo khoảng thời gian (Interval)
```env
SCHEDULE_TYPE=interval
INTERVAL_MINUTES=60    # Mỗi 60 phút = 1 giờ
```

**Ví dụ phổ biến:**
- `INTERVAL_MINUTES=30` - Mỗi 30 phút
- `INTERVAL_MINUTES=60` - Mỗi 1 giờ  
- `INTERVAL_MINUTES=120` - Mỗi 2 giờ
- `INTERVAL_MINUTES=15` - Mỗi 15 phút (tin tức nhanh)

#### 2. Chạy hàng ngày (Daily)
```env
SCHEDULE_TYPE=daily
DAILY_TIME=09:00       # Mỗi ngày lúc 9:00 sáng
```

**Ví dụ:**
- `DAILY_TIME=08:00` - 8:00 sáng
- `DAILY_TIME=14:30` - 2:30 chiều
- `DAILY_TIME=22:00` - 10:00 tối

#### 3. Chạy mỗi giờ (Hourly)
```env
SCHEDULE_TYPE=hourly   # Tự động chạy mỗi giờ
```

#### 4. Chạy nhiều lần trong ngày (Custom)
```env
SCHEDULE_TYPE=custom
CUSTOM_TIMES=06:00,12:00,18:00,22:00  # 4 lần/ngày
```

### 🏃‍♂️ Các cấu hình khác

```env
# Số lượng bài viết tối đa mỗi lần crawl
MAX_ARTICLES=5

# Có chạy ngay khi khởi động không?
RUN_IMMEDIATELY=true

# API endpoint để gửi dữ liệu
API_ENDPOINT=http://localhost:8080/admin/news-articles

# Mức độ log (DEBUG, INFO, WARNING, ERROR)
LOG_LEVEL=INFO
```

## 🚀 Chạy crawler

```bash
python main.py
```