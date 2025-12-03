"""
配置檔案
"""
import os


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'vuln-manager-secret-key-change-in-production')
    
    # MariaDB 連線設定
    DB_HOST = os.environ.get('DB_HOST', 'localhost')
    DB_PORT = os.environ.get('DB_PORT', '3306')
    DB_USER = os.environ.get('DB_USER', 'test')
    DB_PASSWORD = os.environ.get('DB_PASSWORD', 'aabb')
    DB_NAME = os.environ.get('DB_NAME', 'vuln_reports')
    
    @classmethod
    def get(cls, key, default=None):
        return getattr(cls, key, default)
    
    SQLALCHEMY_DATABASE_URI = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # 設為 True 可看到 SQL 語句
    
    # 檔案上傳設定
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
    MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'json'}
    
    # JSON 匯出設定
    EXPORT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
    
    # CORS 設定
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')  # 允許的前端來源，用逗號分隔
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_HEADERS = ['Content-Type', 'Authorization']


class DevelopmentConfig(Config):
    DEBUG = True
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    DEBUG = False


config_map = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}

