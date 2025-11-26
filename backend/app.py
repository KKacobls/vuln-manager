"""
漏洞報告管理系統 - API 伺服器（純後端）
"""
import os
import json
import subprocess
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.utils import secure_filename
from datetime import datetime

from config import config_map, Config
from models import db, Report, Vulnerability, VulnInstance, FixStatus, SeverityLevel, OperationLog
PROT = 10000

def _ensure_database_exists():
    """確保資料庫存在，不存在則建立"""
    import pymysql
    try:
        conn = pymysql.connect(
            host=Config.DB_HOST,
            port=int(Config.DB_PORT),
            user=Config.DB_USER,
            password=Config.DB_PASSWORD,
            charset='utf8mb4'
        )
        db_name = Config.DB_NAME
        with conn.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
        conn.close()
        print(f"✅ 資料庫 '{db_name}' 已就緒")
    except Exception as e:
        print(f"⚠️ 無法自動建立資料庫: {e}")


def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config_map[config_name])
    
    # 設定 CORS
    CORS(app, 
         origins=Config.CORS_ORIGINS,
         methods=Config.CORS_METHODS,
         allow_headers=Config.CORS_HEADERS)
    
    # 確保資料夾存在
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config['EXPORT_FOLDER'], exist_ok=True)
    
    # 自動建立資料庫（如果不存在）
    _ensure_database_exists()
    
    # 初始化資料庫
    db.init_app(app)
    
    with app.app_context():
        db.create_all()
    
    # 引入 services（在 app context 之後）
    from services import ReportService, StatusService, LogService
    
    # ==================== API 路由 ====================
    
    # --- 儀表板統計 ---
    @app.route('/api/dashboard/stats')
    def api_dashboard_stats():
        """取得儀表板統計資料"""
        total_reports = Report.query.count()
        total_vulns = Vulnerability.query.count()
        total_instances = VulnInstance.query.count()
        
        # 嚴重等級統計
        severity_stats = {}
        for level in SeverityLevel:
            count = Vulnerability.query.filter_by(severity=level.value).count()
            severity_stats[level.value] = count
        
        # 修復狀態統計
        status_stats = StatusService.get_status_summary()
        
        # 最近報告
        recent_reports = Report.query.order_by(Report.imported_at.desc()).limit(5).all()
        recent = [{
            'id': r.id,
            'site_url': r.site_url,
            'imported_at': r.imported_at.isoformat(),
            'stats': r.stats
        } for r in recent_reports]
        
        return jsonify({
            'total_reports': total_reports,
            'total_vulnerabilities': total_vulns,
            'total_instances': total_instances,
            'severity_stats': severity_stats,
            'status_stats': status_stats,
            'recent_reports': recent
        })
    
    # --- 報告 CRUD ---
    @app.route('/api/reports', methods=['GET'])
    def api_list_reports():
        """列出所有報告"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        search = request.args.get('search', '')
        
        query = Report.query
        if search:
            query = query.filter(Report.site_url.contains(search))
        
        pagination = query.order_by(Report.imported_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        reports = [{
            'id': r.id,
            'site_url': r.site_url,
            'file_name': r.file_name,
            'imported_at': r.imported_at.isoformat(),
            'notes': r.notes,
            'stats': r.stats,
            'vuln_count': r.vulnerabilities.count()
        } for r in pagination.items]
        
        return jsonify({
            'reports': reports,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    
    @app.route('/api/reports/<int:report_id>', methods=['GET'])
    def api_get_report(report_id):
        """取得單一報告詳情"""
        report = Report.query.get_or_404(report_id)
        
        vulnerabilities = []
        for vuln in report.vulnerabilities:
            instances = [{
                'id': inst.id,
                'url': inst.url,
                'method': inst.method,
                'parameter': inst.parameter,
                'attack': inst.attack,
                'evidence': inst.evidence,
                'other_info': inst.other_info,
                'extra_data': inst.extra_data,
                'fix_status': inst.fix_status,
                'fixed_at': inst.fixed_at.isoformat() if inst.fixed_at else None,
                'fixed_by': inst.fixed_by,
                'fix_notes': inst.fix_notes
            } for inst in vuln.instances]
            
            vulnerabilities.append({
                'id': vuln.id,
                'severity': vuln.severity,
                'title': vuln.title,
                'description': vuln.description,
                'instance_count': len(instances),
                'instances': instances
            })
        
        return jsonify({
            'id': report.id,
            'site_url': report.site_url,
            'summary_sequences': report.summary_sequences,
            'sequence_details': report.sequence_details,
            'file_name': report.file_name,
            'imported_at': report.imported_at.isoformat(),
            'notes': report.notes,
            'stats': report.stats,
            'vulnerabilities': vulnerabilities
        })
    
    @app.route('/api/reports/<int:report_id>', methods=['DELETE'])
    def api_delete_report(report_id):
        """刪除報告"""
        report = Report.query.get_or_404(report_id)
        site_url = report.site_url
        db.session.delete(report)
        db.session.commit()
        
        # 記錄日誌
        LogService.log('DELETE', f'刪除報告: {site_url} (ID: {report_id})')
        
        return jsonify({'success': True, 'message': '報告已刪除'})
    
    @app.route('/api/reports/<int:report_id>/notes', methods=['PUT'])
    def api_update_report_notes(report_id):
        """更新報告備註"""
        report = Report.query.get_or_404(report_id)
        data = request.get_json()
        report.notes = data.get('notes', '')
        db.session.commit()
        return jsonify({'success': True, 'notes': report.notes})
    
    # --- 匯入匯出 ---
    @app.route('/api/import', methods=['POST'])
    def api_import_json():
        """匯入 JSON 檔案"""
        if 'file' not in request.files:
            return jsonify({'error': '未提供檔案'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': '未選擇檔案'}), 400
        
        if not file.filename.endswith('.json'):
            return jsonify({'error': '僅支援 JSON 檔案'}), 400
        
        try:
            json_data = json.load(file)
            report = ReportService.import_json(json_data, file.filename)
            
            # 記錄日誌
            LogService.log('IMPORT', f'匯入報告: {file.filename} → {report.site_url} (ID: {report.id})')
            
            return jsonify({
                'success': True,
                'report_id': report.id,
                'site_url': report.site_url,
                'message': '匯入成功'
            })
        except json.JSONDecodeError:
            return jsonify({'error': 'JSON 格式錯誤'}), 400
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': f'匯入失敗: {str(e)}'}), 500
    
    @app.route('/api/import/bulk', methods=['POST'])
    def api_bulk_import():
        """批次匯入多個 JSON 檔案"""
        if 'files' not in request.files:
            return jsonify({'error': '未提供檔案'}), 400
        
        files = request.files.getlist('files')
        results = {'imported': [], 'errors': []}
        
        for file in files:
            if not file.filename.endswith('.json'):
                results['errors'].append({
                    'file': file.filename,
                    'error': '非 JSON 檔案'
                })
                continue
            
            try:
                json_data = json.load(file)
                report = ReportService.import_json(json_data, file.filename)
                results['imported'].append({
                    'file': file.filename,
                    'report_id': report.id,
                    'site_url': report.site_url
                })
            except Exception as e:
                db.session.rollback()
                results['errors'].append({
                    'file': file.filename,
                    'error': str(e)
                })
        
        # 記錄日誌
        LogService.log('IMPORT', f'批次匯入: 成功 {len(results["imported"])} 個, 失敗 {len(results["errors"])} 個')
        
        return jsonify(results)
    
    @app.route('/api/export/<int:report_id>')
    def api_export_report(report_id):
        """匯出報告為 JSON"""
        include_status = request.args.get('include_status', 'true').lower() == 'true'
        
        try:
            data = ReportService.export_report(report_id, include_status)
            
            # 產生檔案
            filename = f"report_{report_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)
            
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return send_file(filepath, as_attachment=True, download_name=filename)
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # --- 漏洞實例狀態更新 ---
    @app.route('/api/instances/<int:instance_id>/status', methods=['PUT'])
    def api_update_instance_status(instance_id):
        """更新漏洞實例狀態"""
        data = request.get_json()
        status = data.get('status')
        notes = data.get('notes')
        fixed_by = data.get('fixed_by')
        
        if not status:
            return jsonify({'error': '未提供狀態'}), 400
        
        try:
            instance = StatusService.update_instance_status(
                instance_id, status, notes, fixed_by
            )
            
            # 記錄日誌
            LogService.log('STATUS', f'更新狀態: 實例 #{instance_id} → {status}')
            
            return jsonify({
                'success': True,
                'instance_id': instance.id,
                'status': instance.fix_status
            })
        except ValueError as e:
            return jsonify({'error': str(e)}), 400
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    @app.route('/api/instances/batch-status', methods=['PUT'])
    def api_batch_update_status():
        """批次更新漏洞實例狀態"""
        data = request.get_json()
        instance_ids = data.get('instance_ids', [])
        status = data.get('status')
        notes = data.get('notes')
        fixed_by = data.get('fixed_by')
        
        if not instance_ids or not status:
            return jsonify({'error': '參數不完整'}), 400
        
        updated = StatusService.batch_update_status(instance_ids, status, notes, fixed_by)
        
        # 記錄日誌
        LogService.log('STATUS', f'批次更新狀態: {updated} 個實例 → {status}')
        
        return jsonify({
            'success': True,
            'updated_count': updated
        })
    
    # --- 搜尋與篩選 ---
    @app.route('/api/search')
    def api_search():
        """全域搜尋"""
        q = request.args.get('q', '')
        severity = request.args.get('severity')
        status = request.args.get('status')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        
        query = VulnInstance.query.join(Vulnerability).join(Report)
        
        if q:
            query = query.filter(
                db.or_(
                    VulnInstance.url.contains(q),
                    Vulnerability.title.contains(q),
                    Report.site_url.contains(q)
                )
            )
        
        if severity:
            query = query.filter(Vulnerability.severity == severity)
        
        if status:
            query = query.filter(VulnInstance.fix_status == status)
        
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        
        results = [{
            'instance_id': inst.id,
            'url': inst.url,
            'severity': inst.vulnerability.severity,
            'title': inst.vulnerability.title,
            'fix_status': inst.fix_status,
            'report_id': inst.vulnerability.report.id,
            'site_url': inst.vulnerability.report.site_url
        } for inst in pagination.items]
        
        return jsonify({
            'results': results,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    
    # --- 漏洞樹狀結構 ---
    @app.route('/api/tree')
    def api_vuln_tree():
        """取得漏洞樹狀結構（用於檔案樹視圖）"""
        reports = Report.query.order_by(Report.imported_at.desc()).all()
        
        tree = []
        for report in reports:
            report_node = {
                'id': f'report-{report.id}',
                'name': report.site_url or report.file_name,
                'type': 'report',
                'children': []
            }
            
            # 按嚴重等級分組
            severity_groups = {}
            for vuln in report.vulnerabilities:
                if vuln.severity not in severity_groups:
                    severity_groups[vuln.severity] = {
                        'id': f'severity-{report.id}-{vuln.severity}',
                        'name': vuln.severity,
                        'type': 'severity',
                        'children': []
                    }
                
                vuln_node = {
                    'id': f'vuln-{vuln.id}',
                    'name': vuln.title,
                    'type': 'vulnerability',
                    'instance_count': vuln.instances.count(),
                    'children': [{
                        'id': f'instance-{inst.id}',
                        'name': inst.url[:80] + '...' if len(inst.url) > 80 else inst.url,
                        'type': 'instance',
                        'status': inst.fix_status
                    } for inst in vuln.instances]
                }
                severity_groups[vuln.severity]['children'].append(vuln_node)
            
            # 按嚴重等級排序
            severity_order = ['High', 'Medium', 'Low', 'Informational']
            for sev in severity_order:
                if sev in severity_groups:
                    report_node['children'].append(severity_groups[sev])
            
            tree.append(report_node)
        
        return jsonify(tree)
    
    @app.route('/api/tree/<int:report_id>')
    def api_vuln_tree_by_report(report_id):
        """取得單一報告的漏洞樹狀結構"""
        report = Report.query.get_or_404(report_id)
        
        report_node = {
            'id': f'report-{report.id}',
            'name': report.site_url or report.file_name,
            'type': 'report',
            'children': []
        }
        
        # 按嚴重等級分組
        severity_groups = {}
        for vuln in report.vulnerabilities:
            if vuln.severity not in severity_groups:
                severity_groups[vuln.severity] = {
                    'id': f'severity-{report.id}-{vuln.severity}',
                    'name': vuln.severity,
                    'type': 'severity',
                    'children': []
                }
            
            vuln_node = {
                'id': f'vuln-{vuln.id}',
                'name': vuln.title,
                'type': 'vulnerability',
                'instance_count': vuln.instances.count(),
                'children': [{
                    'id': f'instance-{inst.id}',
                    'name': inst.url[:80] + '...' if len(inst.url) > 80 else inst.url,
                    'type': 'instance',
                    'status': inst.fix_status
                } for inst in vuln.instances]
            }
            severity_groups[vuln.severity]['children'].append(vuln_node)
        
        # 按嚴重等級排序
        severity_order = ['High', 'Medium', 'Low', 'Informational']
        for sev in severity_order:
            if sev in severity_groups:
                report_node['children'].append(severity_groups[sev])
        
        return jsonify([report_node])
    
    # --- 操作日誌 ---
    @app.route('/api/logs')
    def api_get_logs():
        """取得操作日誌"""
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)
        action_type = request.args.get('type', '')
        
        query = OperationLog.query
        if action_type:
            query = query.filter(OperationLog.action_type == action_type)
        
        pagination = query.order_by(OperationLog.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        logs = [{
            'id': log.id,
            'action_type': log.action_type,
            'message': log.message,
            'created_at': log.created_at.strftime('%Y-%m-%d %H:%M:%S')
        } for log in pagination.items]
        
        return jsonify({
            'logs': logs,
            'total': pagination.total,
            'pages': pagination.pages,
            'current_page': page
        })
    
    # --- 資料庫管理 ---
    @app.route('/api/db/reset', methods=['POST'])
    def api_reset_database():
        """重置資料庫（需要密碼驗證）"""
        data = request.get_json()
        password = data.get('password', '')
        
        # 驗證密碼
        if password != Config.DB_PASSWORD:
            return jsonify({'error': '密碼錯誤'}), 403
        
        try:
            import pymysql
            conn = pymysql.connect(
                host=Config.DB_HOST,
                port=int(Config.DB_PORT),
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                charset='utf8mb4'
            )
            
            db_name = Config.DB_NAME
            with conn.cursor() as cursor:
                # 刪除資料庫
                cursor.execute(f"DROP DATABASE IF EXISTS `{db_name}`")
                # 重新建立
                cursor.execute(f"CREATE DATABASE `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            conn.close()
            
            # 重新建立表
            with app.app_context():
                db.create_all()
            
            return jsonify({'success': True, 'message': '資料庫已重置'})
        except Exception as e:
            return jsonify({'error': f'重置失敗: {str(e)}'}), 500
    
    @app.route('/api/db/export/sql')
    def api_export_sql():
        """匯出資料庫為 SQL dump"""
        try:
            filename = f"vuln_reports_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            filepath = os.path.join(app.config['EXPORT_FOLDER'], filename)
            
            # 使用 mysqldump
            cmd = [
                'mysqldump',
                '-h', Config.DB_HOST,
                '-P', str(Config.DB_PORT),
                '-u', Config.DB_USER,
                f'-p{Config.DB_PASSWORD}',
                '--single-transaction',
                '--routines',
                '--triggers',
                Config.DB_NAME
            ]
            
            with open(filepath, 'w', encoding='utf-8') as f:
                result = subprocess.run(cmd, stdout=f, stderr=subprocess.PIPE, text=True)
            
            if result.returncode != 0:
                # 如果 mysqldump 失敗，使用 Python 方式匯出
                return _export_sql_python(app, filepath, filename)
            
            LogService.log('EXPORT', f'匯出 SQL: {filename}')
            return send_file(filepath, as_attachment=True, download_name=filename)
        except Exception as e:
            return jsonify({'error': f'匯出失敗: {str(e)}'}), 500
    
    @app.route('/api/db/export/json')
    def api_export_all_json():
        """匯出所有報告為 JSON ZIP"""
        import zipfile
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            zip_filename = f"all_reports_{timestamp}.zip"
            zip_filepath = os.path.join(app.config['EXPORT_FOLDER'], zip_filename)
            
            reports = Report.query.all()
            
            with zipfile.ZipFile(zip_filepath, 'w', zipfile.ZIP_DEFLATED) as zf:
                for report in reports:
                    data = ReportService.export_report(report.id, include_status=True)
                    json_str = json.dumps(data, ensure_ascii=False, indent=2)
                    
                    # 檔名使用 site_url 或 id
                    safe_name = (report.site_url or f'report_{report.id}').replace('://', '_').replace('/', '_')[:50]
                    zf.writestr(f"{safe_name}_{report.id}.json", json_str)
            
            LogService.log('EXPORT', f'匯出全部 JSON: {len(reports)} 個報告')
            return send_file(zip_filepath, as_attachment=True, download_name=zip_filename)
        except Exception as e:
            return jsonify({'error': f'匯出失敗: {str(e)}'}), 500
    
    @app.route('/api/db/import/sql', methods=['POST'])
    def api_import_sql():
        """從 SQL dump 還原資料庫"""
        if 'file' not in request.files:
            return jsonify({'error': '未提供檔案'}), 400
        
        file = request.files['file']
        password = request.form.get('password', '')
        
        # 驗證密碼
        if password != Config.DB_PASSWORD:
            return jsonify({'error': '密碼錯誤'}), 403
        
        if not file.filename.endswith('.sql'):
            return jsonify({'error': '僅支援 .sql 檔案'}), 400
        
        try:
            # 儲存上傳的檔案
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(file.filename))
            file.save(filepath)
            
            import pymysql
            conn = pymysql.connect(
                host=Config.DB_HOST,
                port=int(Config.DB_PORT),
                user=Config.DB_USER,
                password=Config.DB_PASSWORD,
                database=Config.DB_NAME,
                charset='utf8mb4',
                autocommit=True
            )
            
            with open(filepath, 'r', encoding='utf-8') as f:
                sql_content = f.read()
            
            # 分割 SQL 語句執行
            with conn.cursor() as cursor:
                # 簡單分割（以分號結尾）
                statements = sql_content.split(';\n')
                for stmt in statements:
                    stmt = stmt.strip()
                    if stmt and not stmt.startswith('--'):
                        try:
                            cursor.execute(stmt)
                        except Exception as e:
                            print(f"SQL 執行警告: {e}")
            
            conn.close()
            os.remove(filepath)  # 清理上傳的檔案
            
            LogService.log('IMPORT', f'還原 SQL: {file.filename}')
            return jsonify({'success': True, 'message': 'SQL 還原成功'})
        except Exception as e:
            return jsonify({'error': f'還原失敗: {str(e)}'}), 500
    
    return app


def _export_sql_python(app, filepath, filename):
    """使用 Python 方式匯出 SQL（備用方案）"""
    from services import LogService
    import pymysql
    
    conn = pymysql.connect(
        host=Config.DB_HOST,
        port=int(Config.DB_PORT),
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset='utf8mb4'
    )
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(f"-- VulnTracker SQL Dump\n")
        f.write(f"-- Generated: {datetime.now().isoformat()}\n\n")
        f.write(f"SET NAMES utf8mb4;\n")
        f.write(f"SET FOREIGN_KEY_CHECKS = 0;\n\n")
        
        with conn.cursor() as cursor:
            # 取得所有表
            cursor.execute("SHOW TABLES")
            tables = [row[0] for row in cursor.fetchall()]
            
            for table in tables:
                # 取得建表語句
                cursor.execute(f"SHOW CREATE TABLE `{table}`")
                create_stmt = cursor.fetchone()[1]
                f.write(f"DROP TABLE IF EXISTS `{table}`;\n")
                f.write(f"{create_stmt};\n\n")
                
                # 取得資料
                cursor.execute(f"SELECT * FROM `{table}`")
                rows = cursor.fetchall()
                if rows:
                    for row in rows:
                        values = []
                        for val in row:
                            if val is None:
                                values.append('NULL')
                            elif isinstance(val, (int, float)):
                                values.append(str(val))
                            elif isinstance(val, datetime):
                                values.append(f"'{val.strftime('%Y-%m-%d %H:%M:%S')}'")
                            else:
                                escaped = str(val).replace("'", "''").replace("\\", "\\\\")
                                values.append(f"'{escaped}'")
                        
                        f.write(f"INSERT INTO `{table}` VALUES ({', '.join(values)});\n")
                    f.write("\n")
        
        f.write("SET FOREIGN_KEY_CHECKS = 1;\n")
    
    conn.close()
    
    LogService.log('EXPORT', f'匯出 SQL: {filename}')
    return send_file(filepath, as_attachment=True, download_name=filename)


# 主程式入口
if __name__ == '__main__':
    app = create_app('development')
    print("🚀 漏洞報告管理系統 API 伺服器啟動中...")
    print(f"📡 API 端點: http://0.0.0.0:{PROT}/api/")
    print("🔒 CORS 設定: 允許所有來源（開發模式）")
    app.run(host='0.0.0.0', port=PROT, debug=True)

