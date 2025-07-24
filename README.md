# Multi-Source Article Crawler

Flexible web crawler system để crawl bài viết từ nhiều nguồn khác nhau với khả năng cấu hình thời gian chạy linh hoạt qua file `.env`.


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

## ⚙️ Cấu hình chi tiết

### Bật/tắt crawlers

```env
# Bật/tắt từng crawler
ENABLE_COIN98=true              # Bật crawler Coin98
ENABLE_TAPCHIBITCOIN=true       # Bật crawler TapchiBitcoin
```

### 🌐 Cấu hình API endpoints

```env
# API chung (sử dụng nếu không có endpoint riêng)
API_ENDPOINT=http://localhost:8080/admin/news-articles

# API riêng cho từng crawler
COIN98_API_ENDPOINT=http://localhost:8080/admin/coin98-articles
TAPCHIBITCOIN_API_ENDPOINT=http://localhost:8080/admin/tapchibitcoin-articles
```

### 📰 Cấu hình số lượng bài viết

```env
# Số lượng bài viết tối đa cho mỗi crawler
COIN98_MAX_ARTICLES=5
TAPCHIBITCOIN_MAX_ARTICLES=10
```

### 🕐 Cấu hình thời gian chạy

#### 1. Chạy theo khoảng thời gian (Interval)
```env
SCHEDULE_TYPE=interval
INTERVAL_MINUTES=60    # Mỗi 60 phút = 1 giờ
```

#### 2. Chạy hàng ngày (Daily)
```env
SCHEDULE_TYPE=daily
DAILY_TIME=09:00       # Mỗi ngày lúc 9:00 sáng
```

#### 3. Chạy mỗi giờ (Hourly)
```env
SCHEDULE_TYPE=hourly   # Tự động chạy mỗi giờ
```

#### 4. Chạy nhiều lần trong ngày (Custom)
```env
SCHEDULE_TYPE=custom
CUSTOM_TIMES=06:00,12:00,18:00,22:00  # 4 lần/ngày
```

## Chạy crawler

```bash
# Chạy main scheduler
python scheduler.py
```
