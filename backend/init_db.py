#!/usr/bin/env python3
"""
資料庫初始化腳本
執行此腳本來建立資料庫表結構
"""

import pymysql
from config import Config

def create_database():
    """建立資料庫（如果不存在）"""
    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=int(Config.DB_PORT),
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        charset='utf8mb4'
    )
    
    try:
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS {Config.DB_NAME} CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            print(f"✅ 資料庫 '{Config.DB_NAME}' 已建立或已存在")
    finally:
        conn.close()

def create_tables():
    """建立所有表結構"""
    from app import create_app
    from models import db
    
    app = create_app('development')
    with app.app_context():
        db.create_all()
        print("✅ 資料表已建立")

def main():
    print("🔧 初始化資料庫...")
    print(f"   主機: {Config.DB_HOST}:{Config.DB_PORT}")
    print(f"   資料庫: {Config.DB_NAME}")
    print()
    
    try:
        create_database()
        create_tables()
        print()
        print("🎉 資料庫初始化完成！")
        print("   執行 'python app.py' 啟動伺服器")
    except Exception as e:
        print(f"❌ 初始化失敗: {e}")
        raise

if __name__ == '__main__':
    main()
