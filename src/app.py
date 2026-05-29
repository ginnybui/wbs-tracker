import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import gspread
from google.oauth2 import service_account
import time
import math
import os
import re
import base64
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import threading
from urllib.parse import urlparse, parse_qs

# --- 1. CONFIGURATION ---
st.set_page_config(
    page_title="WBS Tracker Pro - Beta Version",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Reset margins, style scrollbars, and frame layout
st.markdown(
    """
    <style>
    * {
        margin: 0 !important;
        padding: 0 !important;
        box-sizing: border-box !important;
    }
    html, body, #root {
        width: 100vw !important;
        height: 100vh !important;
        margin: 0 !important;
        padding: 0 !important;
        overflow: hidden !important;
        background-color: #0b0f19 !important;
    }
    .stApp,
    .stApp div, 
    .stApp section,
    .stApp main {
        width: 100% !important;
        max-width: 100% !important;
        height: 100% !important;
        min-height: 100% !important;
        padding: 0 !important;
        margin: 0 !important;
        border: none !important;
        box-shadow: none !important;
        background: transparent !important;
        background-color: transparent !important;
        transform: none !important;
        filter: none !important;
        perspective: none !important;
    }
    iframe {
        position: fixed !important;
        top: 0 !important;
        left: 0 !important;
        width: 100vw !important;
        height: 100vh !important;
        max-width: 100vw !important;
        max-height: 100vh !important;
        border: none !important;
        margin: 0 !important;
        padding: 0 !important;
        z-index: 999999 !important;
    }
    header[data-testid="stHeader"] { display: none !important; visibility: hidden !important; }
    footer { display: none !important; visibility: hidden !important; }
    [data-testid="stDecoration"] { display: none !important; visibility: hidden !important; }
    [data-testid="stSidebar"] { display: none !important; visibility: hidden !important; }
    </style>
    """,
    unsafe_allow_html=True
)

# --- 2. GOOGLE SHEETS LIVE CONNECTION ---
@st.cache_resource
def get_spreadsheet():
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    gcp_config = dict(st.secrets["gcp"])
    
    if "private_key" in gcp_config:
        try:
            private_key_val = gcp_config["private_key"].strip()
            if private_key_val.startswith("-----BEGIN"):
                gcp_config["private_key"] = private_key_val.replace("\\n", "\n")
            else:
                b64_str = private_key_val
                missing_padding = len(b64_str) % 4
                if missing_padding:
                    b64_str += '=' * (4 - missing_padding)
                decoded_bytes = base64.b64decode(b64_str)
                raw_private_key = decoded_bytes.decode("utf-8")
                if "BEGIN PRIVATE KEY" not in raw_private_key:
                    raw_private_key = f"-----BEGIN PRIVATE KEY-----\n{raw_private_key}\n-----END PRIVATE KEY-----"
                gcp_config["private_key"] = raw_private_key
        except Exception as encode_error:
            raise ValueError(f"Failed to parse private key: {encode_error}")
            
    creds = service_account.Credentials.from_service_account_info(gcp_config, scopes=scope)
    client = gspread.authorize(creds)
    
    target_url = st.secrets["gsheets"]["spreadsheet_url"]
    spreadsheet_key_match = re.search(r"/d/([a-zA-Z0-9-_]+)", target_url)
    if not spreadsheet_key_match:
        raise ValueError("Invalid Google Sheets URL format detected in secrets config.")
        
    spreadsheet_key = spreadsheet_key_match.group(1)
    opened_spreadsheet = client.open_by_key(spreadsheet_key)
    
    # Trỏ trực tiếp và cố định vào tab Data_DEV
    try:
        ws = opened_spreadsheet.worksheet("Data_DEV")
        # Chạy dọn dẹp các dòng dữ liệu bị lệch cột trước đó (Project ID bắt đầu bằng # hoặc TSK)
        cleanup_corrupt_rows(ws)
        seed_default_tasks_if_missing(ws)
        return ws
    except gspread.exceptions.WorksheetNotFound:
        try:
            ws = opened_spreadsheet.add_worksheet(title="Data_DEV", rows="1000", cols="20")
            ensure_headers_exist(ws)
            seed_default_tasks_if_missing(ws)
            return ws
        except Exception:
            return opened_spreadsheet.get_worksheet(0)

PROJECT_MAP = {
    'alpha': 'PRJ-001',
    'beta': 'PRJ-002',
    'gamma': 'PRJ-003',
    'delta': 'PRJ-004',
    'epsilon': 'PRJ-005',
    'zeta': 'PRJ-006'
}

def resolve_project_id(proj):
    proj_clean = str(proj).strip().lower()
    if proj_clean in PROJECT_MAP:
        return PROJECT_MAP[proj_clean]
    for k, v in PROJECT_MAP.items():
        if proj_clean == v.lower():
            return v
    return 'PRJ-001'

def ensure_headers_exist(worksheet):
    try:
        row1 = worksheet.row_values(1)
        headers = ["Project ID", "Task ID", "Title", "Health", "Status", "Est Hours", "Act Hours", "Start Date", "End Date", "Completion %", "Platform", "Description"]
        if not row1 or len(row1) < len(headers):
            worksheet.update(values=[headers], range_name="A1:L1")
    except Exception as e:
        print(f"Failed to ensure headers exist: {e}")

def cleanup_corrupt_rows(worksheet):
    try:
        ensure_headers_exist(worksheet)
        data = worksheet.get_all_records()
        rows_to_delete = []
        for i, record in enumerate(data):
            proj_id = str(record.get('Project ID', '')).strip()
            # Nếu Project ID là #TSK-001 hoặc chứa dấu #, đó là dòng bị lỗi lệch cột
            if proj_id.startswith('#') or proj_id.startswith('TSK'):
                rows_to_delete.append(i + 2)
        
        if rows_to_delete:
            # Sắp xếp giảm dần để chỉ mục không bị lệch khi xóa
            rows_to_delete.sort(reverse=True)
            for r_idx in rows_to_delete:
                worksheet.delete_rows(r_idx)
    except Exception as e:
        print(f"Startup clean failed: {e}")

def seed_default_tasks_if_missing(worksheet):
    try:
        data = worksheet.get_all_records()
        
        project_counts = {
            'PRJ-001': 0,
            'PRJ-002': 0,
            'PRJ-003': 0,
            'PRJ-004': 0,
            'PRJ-005': 0,
            'PRJ-006': 0
        }
        
        for record in data:
            proj = str(record.get('Project ID', '')).strip()
            if proj in project_counts:
                project_counts[proj] += 1
                
        default_seeds = {
            'PRJ-001': [
                ['PRJ-001', '#TSK-001', 'Design Bento UI Layout & Framework Integration', '🟢 Efficient', 'In Progress', 20, 18, '2026-05-01', '2026-05-15', 90, 'Web', 'Establish high-fidelity dashboard structures using modern CSS Grid patterns.'],
                ['PRJ-001', '#TSK-002', 'Configure RBAC Access Validation Layers', '🟢 Efficient', 'Done', 15, 15, '2026-05-05', '2026-05-12', 100, 'CMS', 'Verify roles like Admin, Team Member, and Client against system endpoints.'],
                ['PRJ-001', '#TSK-003', 'Integrate Dynamic Local CSV Parsing Engine', '🔴 Overtime', 'In Progress', 30, 35, '2026-05-10', '2026-05-25', 40, 'Web', 'Parse locally uploaded client CSV files and map them to our internal model.'],
                ['PRJ-001', '#TSK-004', 'Construct Light/Dark Mode Palette Framework', '🟢 Efficient', 'Done', 10, 10, '2026-05-01', '2026-05-05', 100, 'Web', 'Enable Tailwind v4 runtime-based dark mode toggles across all pages.'],
                ['PRJ-001', '#TSK-005', 'Establish Real-Time Top-Center Toast Interactions', '🟢 Efficient', 'To Do', 25, 0, '2026-05-20', '2026-06-01', 0, 'iOS', 'Trigger visual notifications for errors, successes, and alerts.']
            ],
            'PRJ-002': [
                ['PRJ-002', '#TSK-201', 'Develop Stripe Payment Checkout Logic', '🟢 Efficient', 'In Progress', 40, 20, '2026-05-10', '2026-05-20', 50, 'Web', 'Configure standard billing webhook flows.'],
                ['PRJ-002', '#TSK-202', 'Integrate Product Catalog Elastic Search', '🟢 Efficient', 'In Progress', 30, 15, '2026-05-12', '2026-05-25', 50, 'Web', 'Setup index engines and fuzzy search queries.'],
                ['PRJ-002', '#TSK-203', 'Build Admin Inventory Dashboard UI', '🟢 Efficient', 'In Progress', 20, 10, '2026-05-15', '2026-05-28', 50, 'CMS', 'Create CRUD panels to maintain active inventory directories.']
            ],
            'PRJ-003': [
                ['PRJ-003', '#TSK-301', 'Implement Spark Batch Aggregation Scripts', '🟢 Efficient', 'In Progress', 80, 75, '2026-05-01', '2026-05-15', 95, 'Python', 'Compile daily progress telemetry records.'],
                ['PRJ-003', '#TSK-302', 'Setup Snowflake Data Lake Connection Pointers', '🟢 Efficient', 'Done', 50, 50, '2026-05-05', '2026-05-10', 100, 'Snowflake', 'Establish federated credential handshakes.'],
                ['PRJ-003', '#TSK-303', 'Construct Real-Time Grafana Alerts Layer', '🟢 Efficient', 'In Progress', 70, 55, '2026-05-10', '2026-05-22', 78, 'AWS', 'Notify when data pipelines encounter timeout exceptions.']
            ],
            'PRJ-004': [
                ['PRJ-004', '#TSK-401', 'Code Landing Page with Dynamic Carousel Components', '🟢 Efficient', 'Done', 40, 40, '2026-05-01', '2026-05-05', 100, 'Next.js', 'Design interactive hero animations and carousel sliders.'],
                ['PRJ-004', '#TSK-402', 'Audit Lighthouse Core Web Vitals Optimization', '🟢 Efficient', 'Done', 40, 40, '2026-05-06', '2026-05-10', 100, 'Vercel', 'Optimize page loads, LCP metrics, and layout shifts.']
            ],
            'PRJ-005': [
                ['PRJ-005', '#TSK-501', 'Setup Auth0 SSO Authentication Provider', '🟢 Efficient', 'In Progress', 50, 10, '2026-05-12', '2026-05-20', 20, 'React', 'Configure active directory linkages.'],
                ['PRJ-005', '#TSK-502', 'Design Employee Profile Database Schema', '🟢 Efficient', 'In Progress', 40, 20, '2026-05-15', '2026-05-25', 50, 'Node.js', 'Model relations for employee directories.'],
                ['PRJ-005', '#TSK-503', 'Develop CSV Payroll Export Routes', '🟢 Efficient', 'To Do', 30, 0, '2026-05-20', '2026-06-01', 0, 'Node.js', 'Build payroll download spreadsheets.']
            ],
            'PRJ-006': [
                ['PRJ-006', '#TSK-601', 'Build Go Lightweight Port Scanning Tool', '🟢 Efficient', 'To Do', 60, 0, '2026-05-25', '2026-06-05', 0, 'Go', 'Verify network security barriers.'],
                ['PRJ-006', '#TSK-602', 'Deploy Anchore Container Scanner Pipeline', '🟢 Efficient', 'To Do', 50, 0, '2026-05-28', '2026-06-10', 0, 'Docker', 'Analyze production images inside the CI/CD flow.'],
                ['PRJ-006', '#TSK-603', 'Configure Linux Auditd Log Rotation Rules', '🟢 Efficient', 'To Do', 30, 0, '2026-05-30', '2026-06-12', 0, 'Linux', 'Maintain secure system event audits.']
            ]
        }
        
        rows_to_append = []
        for proj, count in project_counts.items():
            if count == 0 and proj in default_seeds:
                rows_to_append.extend(default_seeds[proj])
                
        if rows_to_append:
            print(f"Seeding missing project tasks: {len(rows_to_append)} rows.")
            for row in rows_to_append:
                worksheet.append_row(row)
                time.sleep(0.5)
    except Exception as e:
        print(f"Failed to seed project tasks: {e}")

# --- 3. BACKGROUND REST API SERVER DAEMON ---
class APIHandler(BaseHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        return

    def do_GET(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/tasks':
            try:
                query = parse_qs(parsed_path.query)
                project_param = query.get('project', ['alpha'])[0].strip()
                target_project_id = resolve_project_id(project_param)

                worksheet = get_spreadsheet()
                ensure_headers_exist(worksheet)
                data = worksheet.get_all_records()
                
                tasks_list = []
                for idx, record in enumerate(data):
                    proj_id = str(record.get('Project ID', '')).strip()
                    if proj_id != target_project_id:
                        continue

                    # Trích xuất Task ID từ cột 'Task ID'
                    task_id_raw = str(record.get('Task ID', '')).strip()
                    # Định dạng sang chuỗi WBS cao cấp '#TSK-XXX'
                    try:
                        task_id_num = int(float(task_id_raw))
                        task_id_formatted = f"#TSK-{str(task_id_num).zfill(3)}"
                    except:
                        m = re.search(r'\d+', task_id_raw)
                        if m:
                            task_id_formatted = f"#TSK-{m.group(0).zfill(3)}"
                        else:
                            task_id_formatted = task_id_raw if task_id_raw.startswith('#') else f"#{task_id_raw}"

                    completion_val = 0
                    try:
                        completion_val = int(float(record.get('Completion %', 0)))
                    except:
                        pass
                        
                    est_val = 0.0
                    try:
                        est_val = float(record.get('Est Hours', 0.0))
                    except:
                        pass
                        
                    act_val = 0.0
                    try:
                        act_val = float(record.get('Act Hours', 0.0))
                    except:
                        pass

                    tasks_list.append({
                        'id': task_id_formatted,
                        'title': str(record.get('Title', 'Untitled')).strip(),
                        'health': str(record.get('Health', '🟢 Efficient')).strip(),
                        'status': str(record.get('Status', 'To Do')).strip(),
                        'est': est_val,
                        'act': act_val,
                        'startDate': str(record.get('Start Date', '')).strip(),
                        'endDate': str(record.get('End Date', '')).strip(),
                        'progress': completion_val,
                        'platform': str(record.get('Platform', 'Web')).strip(),
                        'description': str(record.get('Description', '')).strip()
                    })

                # Sắp xếp danh sách task theo số ID giảm dần (mới nhất lên đầu)
                def get_task_num(t):
                    match = re.search(r'\d+', t['id'])
                    return int(match.group(0)) if match else 0
                tasks_list.sort(key=get_task_num, reverse=True)

                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(tasks_list).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/tasks':
            try:
                query = parse_qs(parsed_path.query)
                project_param = query.get('project', [''])[0].strip()
                
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                task_data = json.loads(body.decode('utf-8'))
                
                if not project_param:
                    project_param = task_data.get('projectId', 'alpha')
                
                target_project_id = resolve_project_id(project_param)
                
                worksheet = get_spreadsheet()
                ensure_headers_exist(worksheet)
                
                existing = worksheet.get_all_records()
                # Tìm Task ID lớn nhất trong dự án này để tăng tự động
                max_task_id = 0
                for r in existing:
                    proj = str(r.get('Project ID', '')).strip()
                    if proj == target_project_id:
                        tid_raw = str(r.get('Task ID', 0)).strip()
                        if tid_raw:
                            try:
                                tid = int(float(tid_raw))
                            except ValueError:
                                match_tid = re.search(r'\d+', tid_raw)
                                tid = int(match_tid.group(0)) if match_tid else 0
                            if tid > max_task_id:
                                max_task_id = tid
                
                if max_task_id == 0:
                    start_map = {
                        'PRJ-001': 1,
                        'PRJ-002': 201,
                        'PRJ-003': 301,
                        'PRJ-004': 401,
                        'PRJ-005': 501,
                        'PRJ-006': 601
                    }
                    new_task_id = start_map.get(target_project_id, 1)
                else:
                    new_task_id = max_task_id + 1
                new_id_formatted = f"#TSK-{str(new_task_id).zfill(3)}"
                
                title = task_data.get('title', 'New Task')
                status = task_data.get('status', 'TODO')
                
                status_map = {
                    'TODO': 'To Do',
                    'IN_PROGRESS': 'In Progress',
                    'DONE': 'Done',
                    'ON_HOLD': 'On Hold'
                }
                sheet_status = status_map.get(status, status)
                
                est = float(task_data.get('est', 0.0))
                act = float(task_data.get('act', 0.0))
                start_date = task_data.get('startDate', '')
                end_date = task_data.get('endDate', '')
                progress = int(task_data.get('progress', 100 if status == 'DONE' else 0))
                platform = task_data.get('platform', 'Web')
                description = task_data.get('description', '')
                health = "🟢 Efficient" if act <= est else "🔴 Overtime"
                
                # Cột theo thứ tự: Project ID, Task ID, Title, Health, Status, Est Hours, Act Hours, Start Date, End Date, Completion %, Platform, Description
                new_row = [target_project_id, new_id_formatted, title, health, sheet_status, est, act, start_date, end_date, progress, platform, description]
                worksheet.append_row(new_row)
                
                self.send_response(201)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True, "id": new_id_formatted}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_PUT(self):
        if self.path == '/api/tasks':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length)
                task_data = json.loads(body.decode('utf-8'))
                
                worksheet = get_spreadsheet()
                ensure_headers_exist(worksheet)
                
                all_records = worksheet.get_all_records()
                target_id = task_data.get('id', '')
                
                # Lấy số nguyên từ chuỗi ID '#TSK-009' -> 9
                match = re.search(r'\d+', target_id)
                if not match:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Invalid Task ID format"}).encode('utf-8'))
                    return
                target_task_num = int(match.group(0))
                
                row_index = -1
                target_project_id = "PRJ-001"
                for i, r in enumerate(all_records):
                    # Tìm dòng có Task ID khớp số (Task ID là duy nhất trên toàn bộ bảng)
                    try:
                        task_id_raw = str(r.get('Task ID', '')).strip()
                        try:
                            task_id_num = int(float(task_id_raw))
                        except ValueError:
                            m = re.search(r'\d+', task_id_raw)
                            task_id_num = int(m.group(0)) if m else -1
                    except:
                        task_id_num = -1
                        
                    if task_id_num == target_task_num:
                        row_index = i + 2
                        target_project_id = str(r.get('Project ID', 'PRJ-001')).strip()
                        break
                
                if row_index == -1:
                    self.send_response(404)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": f"Task number {target_task_num} not found in Google Sheets"}).encode('utf-8'))
                    return
                
                title = task_data.get('title')
                status = task_data.get('status')
                
                status_map = {
                    'TODO': 'To Do',
                    'IN_PROGRESS': 'In Progress',
                    'DONE': 'Done',
                    'ON_HOLD': 'On Hold'
                }
                sheet_status = status_map.get(status, status)
                
                est = float(task_data.get('est', 0.0))
                act = float(task_data.get('act', 0.0))
                start_date = task_data.get('startDate', '')
                end_date = task_data.get('endDate', '')
                progress = int(task_data.get('progress', 100 if status == 'DONE' else 0))
                platform = task_data.get('platform', 'Web')
                description = task_data.get('description', '')
                health = "🟢 Efficient" if act <= est else "🔴 Overtime"
                
                # Sắp xếp chuẩn cột
                headers = [h.strip() for h in worksheet.row_values(1)]
                row_values = [""] * len(headers)
                for col_idx, h in enumerate(headers):
                    if h == "Project ID": row_values[col_idx] = target_project_id
                    elif h == "Task ID": row_values[col_idx] = f"#TSK-{str(target_task_num).zfill(3)}"
                    elif h == "Title": row_values[col_idx] = title
                    elif h == "Health": row_values[col_idx] = health
                    elif h == "Status": row_values[col_idx] = sheet_status
                    elif h == "Est Hours": row_values[col_idx] = est
                    elif h == "Act Hours": row_values[col_idx] = act
                    elif h == "Start Date": row_values[col_idx] = start_date
                    elif h == "End Date": row_values[col_idx] = end_date
                    elif h == "Completion %": row_values[col_idx] = progress
                    elif h == "Platform": row_values[col_idx] = platform
                    elif h == "Description": row_values[col_idx] = description

                end_col_a1 = gspread.utils.rowcol_to_a1(row_index, len(headers))
                worksheet.update(values=[row_values], range_name=f"A{row_index}:{end_col_a1}")
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

    def do_DELETE(self):
        parsed_path = urlparse(self.path)
        if parsed_path.path == '/api/tasks':
            try:
                query = parse_qs(parsed_path.query)
                target_id = query.get('id', [''])[0]
                
                if not target_id:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "ID parameter missing"}).encode('utf-8'))
                    return
                
                # Trích xuất các số Task ID từ danh sách gửi lên
                target_ids = [tid.strip() for tid in target_id.split(',') if tid.strip()]
                target_nums = []
                for tid in target_ids:
                    match = re.search(r'\d+', tid)
                    if match:
                        target_nums.append(int(match.group(0)))
                
                worksheet = get_spreadsheet()
                all_records = worksheet.get_all_records()
                
                rows_to_delete = []
                for i, r in enumerate(all_records):
                    try:
                        task_id_raw = str(r.get('Task ID', '')).strip()
                        try:
                            task_id_num = int(float(task_id_raw))
                        except ValueError:
                            m = re.search(r'\d+', task_id_raw)
                            task_id_num = int(m.group(0)) if m else -1
                    except:
                        task_id_num = -1
                        
                    if task_id_num in target_nums:
                        rows_to_delete.append(i + 2)
                
                rows_to_delete.sort(reverse=True)
                for r_idx in rows_to_delete:
                    worksheet.delete_rows(r_idx)
                
                self.send_response(200)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps({"success": True}).encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_api_server():
    server_address = ('127.0.0.1', 8001)
    httpd = HTTPServer(server_address, APIHandler)
    httpd.serve_forever()

if 'api_server_started' not in st.session_state:
    st.session_state['api_server_started'] = True
    t = threading.Thread(target=run_api_server, daemon=True)
    t.start()

# --- 4. RENDER DYNAMIC MOCKUP IFRAME ---
base_path = os.path.dirname(os.path.abspath(__file__))
html_file_path = os.path.join(os.path.dirname(base_path), "dashboard_preview.html")

try:
    with open(html_file_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    components.html(html_content, height=1400, scrolling=True)
except Exception as e:
    st.error(f"Failed to load Alpha Mockup layout: {e}")