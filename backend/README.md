# 漏洞報告管理系統 - 後端 API 伺服器

這是純後端 API 伺服器，提供 RESTful API 給前端使用。

## 功能

- 純 API 服務，不提供 HTML 頁面
- 支援 CORS，可與不同 IP 的前端連線
- 提供完整的漏洞報告管理 API

## 安裝

```bash
pip install -r requirements.txt
```

## 設定

編輯 `config.py` 或設定環境變數：

- `DB_HOST`: 資料庫主機（預設: localhost）
- `DB_PORT`: 資料庫埠號（預設: 3307）
- `DB_USER`: 資料庫使用者（預設: root）
- `DB_PASSWORD`: 資料庫密碼（預設: password）
- `DB_NAME`: 資料庫名稱（預設: vuln_reports）
- `CORS_ORIGINS`: 允許的前端來源，用逗號分隔（預設: *，允許所有來源）

## 執行

```bash
python app.py
```

伺服器會在 `http://0.0.0.0:5000` 啟動。

## API 端點

所有 API 端點都以 `/api` 為前綴：

- `GET /api/dashboard/stats` - 取得儀表板統計
- `GET /api/reports` - 列出報告
- `GET /api/reports/<id>` - 取得報告詳情
- `DELETE /api/reports/<id>` - 刪除報告
- `POST /api/import` - 匯入 JSON 報告
- `PUT /api/instances/<id>/status` - 更新漏洞狀態
- 等等...

## CORS 設定

在 `config.py` 中設定 `CORS_ORIGINS` 來控制允許的前端來源：

```python
CORS_ORIGINS = ['http://192.168.1.100', 'http://192.168.1.101']
```

或使用環境變數：

```bash
export CORS_ORIGINS="http://192.168.1.100,http://192.168.1.101"
```

