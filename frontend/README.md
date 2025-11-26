# 漏洞報告管理系統 - 前端

這是純前端靜態網站，可以部署在任何網頁伺服器上（如 Nginx、Apache）。

## 設定

編輯 `config.js` 來設定後端 API 的 URL：

```javascript
const API_CONFIG = {
    BASE_URL: 'http://192.168.1.100:5000',  // 後端 API 的 IP 和埠號
    API_PREFIX: '/api'
};
```

## 部署

### 方式 1: 使用 Nginx

1. 將 `frontend` 資料夾內容複製到 Nginx 的網頁根目錄（如 `/var/www/html`）
2. 設定 Nginx：

```nginx
server {
    listen 80;
    server_name your-frontend-ip;
    root /var/www/html;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

### 方式 2: 使用 Apache

1. 將 `frontend` 資料夾內容複製到 Apache 的網頁根目錄（如 `/var/www/html`）
2. 啟用 `.htaccess` 支援（如果需要）

### 方式 3: 使用 Python SimpleHTTPServer（開發用）

```bash
cd frontend
python -m http.server 8080
```

然後在瀏覽器開啟 `http://localhost:8080`

## 檔案結構

```
frontend/
├── index.html          # 儀表板
├── reports.html        # 報告列表
├── report_detail.html  # 報告詳情
├── logs.html          # 操作日誌
├── settings.html      # 系統設定
├── config.js          # API 設定檔
├── css/
│   └── style.css      # 樣式表
└── js/
    ├── common.js       # 通用函數
    ├── dashboard.js    # 儀表板邏輯
    ├── reports.js     # 報告列表邏輯
    └── report_detail.js # 報告詳情邏輯
```

## 注意事項

- 確保 `config.js` 中的 `BASE_URL` 指向正確的後端 API 伺服器
- 後端必須設定 CORS 允許前端來源
- 所有 API 呼叫都透過 `config.js` 中的設定進行

