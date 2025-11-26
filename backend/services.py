"""
JSON 報告匯入匯出服務
"""
import json
import os
from datetime import datetime
from models import db, Report, Vulnerability, VulnInstance, FixStatus


class ReportService:
    """報告匯入匯出服務"""
    
    SEVERITY_KEYS = {'High', 'Medium', 'Low', 'Informational'}
    CONTENT_FIELDS = {'方法', 'Parameter', '攻擊', 'Evidence', 'Other Info'}
    
    @staticmethod
    def import_json(json_data: dict, file_name: str = None) -> Report:
        """
        匯入 JSON 報告到資料庫
        
        Args:
            json_data: 解析後的 JSON 資料
            file_name: 原始檔名
            
        Returns:
            Report: 建立的報告物件
        """
        # 建立報告
        report = Report(
            site_url=json_data.get('SiteURL', ''),
            summary_sequences=json_data.get('SummaryofSequences', ''),
            sequence_details=json_data.get('SequenceDetails', ''),
            file_name=file_name
        )
        db.session.add(report)
        db.session.flush()  # 取得 report.id
        
        # 處理各嚴重等級的漏洞
        for severity in ReportService.SEVERITY_KEYS:
            if severity not in json_data:
                continue
                
            vuln_list = json_data[severity]
            if not isinstance(vuln_list, list):
                continue
                
            for vuln_obj in vuln_list:
                # 每個 vuln_obj 是 {title: {Description: ..., instances: [...]}}
                for title, vuln_data in vuln_obj.items():
                    if not isinstance(vuln_data, dict):
                        continue
                    
                    # 建立漏洞類型
                    vulnerability = Vulnerability(
                        report_id=report.id,
                        severity=severity,
                        title=title,
                        description=vuln_data.get('Description', '')
                    )
                    db.session.add(vulnerability)
                    db.session.flush()
                    
                    # 處理漏洞實例
                    instances = vuln_data.get('instances', [])
                    for inst in instances:
                        if not isinstance(inst, dict):
                            continue
                        
                        content = inst.get('content', {})
                        extra_data = {}
                        
                        # 收集非標準欄位
                        for key, value in inst.items():
                            if key not in ('URL', 'content', '方法', 'Parameter', '攻擊', 'Evidence', 'Other Info'):
                                extra_data[key] = value
                        
                        instance = VulnInstance(
                            vulnerability_id=vulnerability.id,
                            url=inst.get('URL', ''),
                            method=content.get('方法', inst.get('方法', '')),
                            parameter=content.get('Parameter', inst.get('Parameter', '')),
                            attack=content.get('攻擊', inst.get('攻擊', '')),
                            evidence=content.get('Evidence', inst.get('Evidence', '')),
                            other_info=content.get('Other Info', inst.get('Other Info', '')),
                            extra_data=extra_data if extra_data else None
                        )
                        db.session.add(instance)
        
        db.session.commit()
        return report
    
    @staticmethod
    def import_json_file(file_path: str) -> Report:
        """從檔案匯入 JSON"""
        with open(file_path, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        file_name = os.path.basename(file_path)
        return ReportService.import_json(json_data, file_name)
    
    @staticmethod
    def import_json_string(json_string: str, file_name: str = None) -> Report:
        """從 JSON 字串匯入"""
        json_data = json.loads(json_string)
        return ReportService.import_json(json_data, file_name)
    
    @staticmethod
    def export_report(report_id: int, include_status: bool = True) -> dict:
        """
        匯出報告為 JSON 格式
        
        Args:
            report_id: 報告 ID
            include_status: 是否包含修復狀態資訊
            
        Returns:
            dict: 報告的 JSON 格式資料
        """
        report = Report.query.get_or_404(report_id)
        
        output = {
            'SiteURL': report.site_url,
            'SummaryofSequences': report.summary_sequences,
            'SequenceDetails': report.sequence_details,
            'exported_at': datetime.utcnow().isoformat(),
        }
        
        if report.notes:
            output['report_notes'] = report.notes
        
        # 組織漏洞資料
        for vuln in report.vulnerabilities:
            severity = vuln.severity
            if severity not in output:
                output[severity] = []
            
            vuln_data = {
                'Description': vuln.description,
                'instances': []
            }
            
            for inst in vuln.instances:
                inst_data = {
                    'URL': inst.url,
                    'content': {}
                }
                
                if inst.method:
                    inst_data['content']['方法'] = inst.method
                if inst.parameter:
                    inst_data['content']['Parameter'] = inst.parameter
                if inst.attack:
                    inst_data['content']['攻擊'] = inst.attack
                if inst.evidence:
                    inst_data['content']['Evidence'] = inst.evidence
                if inst.other_info:
                    inst_data['content']['Other Info'] = inst.other_info
                
                if inst.extra_data:
                    inst_data.update(inst.extra_data)
                
                # 加入修復狀態
                if include_status:
                    inst_data['_fix_status'] = {
                        'status': inst.fix_status,
                        'fixed_at': inst.fixed_at.isoformat() if inst.fixed_at else None,
                        'fixed_by': inst.fixed_by,
                        'notes': inst.fix_notes
                    }
                
                vuln_data['instances'].append(inst_data)
            
            output[severity].append({vuln.title: vuln_data})
        
        return output
    
    @staticmethod
    def bulk_import_directory(directory: str) -> list:
        """批次匯入目錄下所有 JSON 檔案"""
        imported = []
        errors = []
        
        for filename in os.listdir(directory):
            if not filename.endswith('.json'):
                continue
            
            file_path = os.path.join(directory, filename)
            try:
                report = ReportService.import_json_file(file_path)
                imported.append({
                    'file': filename,
                    'report_id': report.id,
                    'site_url': report.site_url
                })
            except Exception as e:
                errors.append({
                    'file': filename,
                    'error': str(e)
                })
        
        return {'imported': imported, 'errors': errors}


class StatusService:
    """修復狀態管理服務"""
    
    @staticmethod
    def update_instance_status(instance_id: int, status: str, notes: str = None, fixed_by: str = None) -> VulnInstance:
        """更新漏洞實例狀態"""
        instance = VulnInstance.query.get_or_404(instance_id)
        
        if status not in [s.value for s in FixStatus]:
            raise ValueError(f"無效狀態: {status}")
        
        instance.fix_status = status
        instance.fix_notes = notes
        
        if status == FixStatus.FIXED.value:
            instance.fixed_at = datetime.utcnow()
            instance.fixed_by = fixed_by
        
        db.session.commit()
        return instance
    
    @staticmethod
    def batch_update_status(instance_ids: list, status: str, notes: str = None, fixed_by: str = None) -> int:
        """批次更新多個實例狀態"""
        updated = 0
        for inst_id in instance_ids:
            try:
                StatusService.update_instance_status(inst_id, status, notes, fixed_by)
                updated += 1
            except Exception:
                continue
        return updated
    
    @staticmethod
    def get_status_summary(report_id: int = None) -> dict:
        """取得狀態統計"""
        query = VulnInstance.query
        if report_id:
            query = query.join(Vulnerability).filter(Vulnerability.report_id == report_id)
        
        summary = {s.value: 0 for s in FixStatus}
        for instance in query.all():
            if instance.fix_status in summary:
                summary[instance.fix_status] += 1
        
        summary['total'] = sum(summary.values())
        return summary


class LogService:
    """操作日誌服務"""
    
    @staticmethod
    def log(action_type: str, message: str):
        """記錄操作日誌"""
        from models import OperationLog
        log = OperationLog(
            action_type=action_type,
            message=message
        )
        db.session.add(log)
        db.session.commit()
        return log
    
    @staticmethod
    def get_logs(page: int = 1, per_page: int = 50, action_type: str = None):
        """取得日誌列表"""
        from models import OperationLog
        query = OperationLog.query
        if action_type:
            query = query.filter(OperationLog.action_type == action_type)
        return query.order_by(OperationLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
