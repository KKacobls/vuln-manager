"""
漏洞報告管理系統 - 資料庫模型
"""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
from enum import Enum

db = SQLAlchemy()


class FixStatus(Enum):
    PENDING = "pending"          # 待處理
    IN_PROGRESS = "in_progress"  # 處理中
    FIXED = "fixed"              # 已修復
    WONT_FIX = "wont_fix"        # 不修復
    FALSE_POSITIVE = "false_positive"  # 誤報


class SeverityLevel(Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    INFORMATIONAL = "Informational"


class Report(db.Model):
    """掃描報告主表"""
    __tablename__ = 'reports'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    site_url = db.Column(db.String(500), nullable=False, index=True)
    summary_sequences = db.Column(db.Text)
    sequence_details = db.Column(db.Text)
    file_name = db.Column(db.String(255))  # 原始 JSON 檔名
    imported_at = db.Column(db.DateTime, default=datetime.utcnow)
    notes = db.Column(db.Text)  # 報告級別備註
    
    # 關聯
    vulnerabilities = db.relationship('Vulnerability', backref='report', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Report {self.id}: {self.site_url}>'
    
    @property
    def stats(self):
        """統計各嚴重等級數量"""
        stats = {s.value: 0 for s in SeverityLevel}
        for vuln in self.vulnerabilities:
            if vuln.severity in stats:
                stats[vuln.severity] += 1
        return stats


class Vulnerability(db.Model):
    """漏洞類型表"""
    __tablename__ = 'vulnerabilities'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    report_id = db.Column(db.Integer, db.ForeignKey('reports.id', ondelete='CASCADE'), nullable=False, index=True)
    severity = db.Column(db.String(50), nullable=False, index=True)  # High, Medium, Low, Informational
    title = db.Column(db.String(500), nullable=False)
    description = db.Column(db.Text)
    
    # 關聯
    instances = db.relationship('VulnInstance', backref='vulnerability', lazy='dynamic', cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Vulnerability {self.severity}: {self.title}>'


class VulnInstance(db.Model):
    """漏洞實例表（每個 URL 的具體漏洞）"""
    __tablename__ = 'vuln_instances'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    vulnerability_id = db.Column(db.Integer, db.ForeignKey('vulnerabilities.id', ondelete='CASCADE'), nullable=False, index=True)
    url = db.Column(db.Text, nullable=False)
    method = db.Column(db.String(20))  # GET, POST 等
    parameter = db.Column(db.String(255))
    attack = db.Column(db.Text)
    evidence = db.Column(db.Text)
    other_info = db.Column(db.Text)
    extra_data = db.Column(db.JSON)  # 其他欄位以 JSON 儲存
    
    # 修復狀態追蹤
    fix_status = db.Column(db.String(50), default=FixStatus.PENDING.value, index=True)
    fixed_at = db.Column(db.DateTime)
    fixed_by = db.Column(db.String(100))
    fix_notes = db.Column(db.Text)  # 修復備註
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<VulnInstance {self.id}: {self.url[:50]}>'


class OperationLog(db.Model):
    """操作日誌表"""
    __tablename__ = 'operation_logs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    action_type = db.Column(db.String(50), nullable=False, index=True)  # IMPORT, DELETE, STATUS, EXPORT
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f'<Log {self.action_type}: {self.message[:30]}>'


# 初始化資料庫輔助函數
def init_db(app):
    """初始化資料庫"""
    db.init_app(app)
    with app.app_context():
        db.create_all()
        print("資料庫表已建立")
