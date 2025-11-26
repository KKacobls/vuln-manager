from flask import Flask, send_from_directory
import os

# 初始化 Flask
# static_folder 設定為當前目錄 ('.')
# static_url_path='' 表示不需要 /static 前綴，直接對應根目錄
app = Flask(__name__, static_folder='.', static_url_path='')

@app.route('/')
def index():
    """
    當使用者訪問根目錄 (http://localhost:8000/) 時，
    直接回傳 index.html
    """
    return send_from_directory('.', 'index.html')

@app.route('/<path:path>')
def serve_static(path):
    """
    處理所有其他檔案請求
    例如: /css/style.css, /js/common.js, /reports.html
    """
    # 檢查檔案是否存在，避免報錯
    if os.path.exists(path):
        return send_from_directory('.', path)
    else:
        return f"找不到檔案: {path}", 404

if __name__ == '__main__':
    # 設定 Port 為 8000，與後端的 5000 或 10000 錯開
    # host='0.0.0.0' 代表允許外部 IP (如手機、學長電腦) 連線
    port = 8000
    print(f"=================================================")
    print(f"前端伺服器已啟動！")
    print(f"本機訪問: http://127.0.0.1:{port}")
    print(f"外部訪問: http://IP:{port}")
    print(f"=================================================")
    
    app.run(host='0.0.0.0', port=port, debug=True)
    #app.run(host='0.0.0.0', port=5000, debug=True)