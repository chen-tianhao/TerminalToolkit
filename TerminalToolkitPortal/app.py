#!/usr/bin/env python3
"""
TerminalToolkit Portal - 统一入口
将 LayoutDesigner、EFD-Analyzer、WharfToolkit 三个项目整合到统一入口
"""
import os
import sys
import io
import subprocess
import threading
import time
import signal
from pathlib import Path

from flask import Flask, render_template_string, Response, request, send_file, session, redirect

# 添加项目路径
# 尝试多个可能的路径结构
app_dir = Path(__file__).resolve().parent
possible_bases = [
    app_dir.parent,                          # TerminalToolkitPortal/ 的父目录
    Path(__file__).resolve(),               # 当前文件目录
]

# 找到正确的项目根目录（包含 LayoutDesigner, EFD-Analyzer 等）
BASE_DIR = None
for base in possible_bases:
    if (base / "LayoutDesigner").exists() and (base / "EFD-Analyzer").exists():
        BASE_DIR = base
        break

if BASE_DIR is None:
    # 默认使用父目录
    BASE_DIR = app_dir.parent

print(f"BASE_DIR: {BASE_DIR}")

LAYOUT_DESIGNER_DIR = BASE_DIR / "LayoutDesigner"
EFD_ANALYZER_DIR = BASE_DIR / "EFD-Analyzer"
WHARF_TOOLKIT_DIR = BASE_DIR / "WharfToolkit"

# 内部服务端口
DASH_PORT = 8050
FASTAPI_PORT = 8000

# 存储子进程
subprocesses = []

app = Flask(__name__)
app.secret_key = 'wharf-util-secret-key'  # 用于 session

# ==================== 访问计数器 ====================
visit_counts = {
    'layout-designer': 0,
    'efd-analyzer': 0,
    'wharf-util': 0
}

def get_total_visits():
    """获取所有子应用的访问次数总和"""
    return sum(visit_counts.values())

def get_visit_info(app_name):
    """获取单个应用的访问信息"""
    return {
        'app_visit': visit_counts[app_name],
        'total_visits': get_total_visits()
    }

# ==================== 首页 ====================

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Terminal Toolkit</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            padding: 50px;
            text-align: center;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            margin: 0;
        }
        h1 {
            color: white;
            font-size: 48px;
            margin-bottom: 50px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .container {
            max-width: 900px;
            margin: 0 auto;
        }
        .card {
            display: inline-block;
            margin: 20px;
            padding: 50px 60px;
            background: white;
            border: none;
            border-radius: 20px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.3);
            transition: transform 0.3s, box-shadow 0.3s;
            text-decoration: none;
        }
        .card:hover {
            transform: translateY(-10px);
            box-shadow: 0 15px 40px rgba(0,0,0,0.4);
        }
        a {
            text-decoration: none;
            color: #333;
            font-size: 28px;
            font-weight: bold;
        }
        a:hover {
            color: #667eea;
        }
        p {
            color: #666;
            font-size: 16px;
            margin-top: 10px;
        }
        .nav-link {
            display: inline-block;
            margin: 10px 20px;
            padding: 15px 30px;
            background: white;
            color: #667eea;
            border-radius: 50px;
            text-decoration: none;
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
        }
        .nav-link:hover {
            background: #667eea;
            color: white;
        }
        .visit-counter {
            color: #ccc;
            font-size: 14px;
            margin-top: 30px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Terminal Toolkit</h1>
        <p class="visit-counter">This is the {{ total_visits }}th visit in total.</p>
        <div class="card">
            <a href="/layout-designer" target="_blank">Layout Designer</a>
        </div>
        <div class="card">
            <a href="/efd-analyzer" target="_blank">EFD Analyzer</a>
        </div>
        <div class="card">
            <a href="/wharf-util" target="_blank">Wharf Utilization</a>
        </div>
        </div>
    </div>
</body>
</html>
'''

WHARF_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Wharf Utilization</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            padding: 20px;
            background: #f5f5f5;
            min-height: 100vh;
            margin: 0;
        }
        h1 {
            color: #333;
            text-align: center;
        }
        .chart-container {
            max-width: 900px;
            margin: 30px auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .chart-container h2 {
            color: #667eea;
            margin-top: 0;
        }
        .chart-container img {
            max-width: 100%;
            height: auto;
        }
        .nav-link {
            display: inline-block;
            margin: 10px;
            padding: 10px 20px;
            background: #667eea;
            color: white;
            border-radius: 5px;
            text-decoration: none;
        }
        .nav-link:hover {
            background: #764ba2;
        }
        .loading {
            text-align: center;
            color: #666;
            padding: 40px;
        }
        .visit-counter {
            color: #999;
            font-size: 14px;
            text-align: center;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <h1>Wharf Utilization 分析</h1>
    <p class="visit-counter">This is the {{ app_visit }}th visit for current function. ({{ total_visits }} visits in total)</p>
    <div style="text-align: center;">
        <a href="/" class="nav-link">Back To Home</a>
        <a href="/wharf-util/download" class="nav-link" download>Download Example Data</a>
    </div>
    <div class="chart-container" style="text-align: center;">
        <h2>Upload Data File</h2>
        <form action="/wharf-util/upload" method="post" enctype="multipart/form-data" style="display: inline-block;">
            <input type="file" name="file" accept=".json" required style="margin: 10px 0;">
            <br>
            <button type="submit" class="nav-link">Upload & Visualize</button>
        </form>
        {% if uploaded_file %}
        <p style="color: green; margin-top: 10px;">Current file: {{ uploaded_file }}</p>
        {% else %}
        <p style="color: red; margin-top: 10px;">Please upload a JSON file to view the chart</p>
        {% endif %}
    </div>
    {% if uploaded_file %}
    <div class="chart-container">
        <h2>Wharf N</h2>
        <img src="/wharf-util/chart/n" alt="Wharf N Chart" />
    </div>
    <div class="chart-container">
        <h2>Wharf S</h2>
        <img src="/wharf-util/chart/s" alt="Wharf S Chart" />
    </div>
    {% endif %}
</body>
</html>
'''


# ==================== 代理转发 ====================

def proxy_request(target_port, path, base_path='', app_name=''):
    """代理请求到内部服务"""
    import requests

    # 如果路径不以 / 开头，加上 /
    if not path.startswith('/'):
        path = '/' + path

    target_url = f"http://localhost:{target_port}{path}"
    try:
        resp = requests.request(
            method=request.method,
            url=target_url,
            headers={key: value for key, value in request.headers if key.lower() not in ('host', 'connection')},
            data=request.get_data(),
            params=request.args,
            cookies=request.cookies,
            allow_redirects=False,
            timeout=30
        )

        # 处理重定向 - 重写 Location 头
        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get('Location', '')
            if location.startswith('http://localhost:' + str(target_port)):
                # 重写内部 URL 为代理路径
                location = location.replace(f'http://localhost:{target_port}', base_path)
            return Response(
                resp.content,
                resp.status_code,
                {'Location': location}
            )

        # 重写响应中的资源路径 (CSS, JS, images)
        content_type = resp.headers.get('content-type', '')
        if 'text/html' in content_type:
            # 重写响应中的路径
            content = resp.text
            if base_path:
                # 仅替换 URL 路径中的 /_dash（带前导斜杠），不动 HTML 属性中的 _dash
                content = content.replace('"/_dash', f'"{base_path}/_dash')
                content = content.replace("'/_dash", f"'{base_path}/_dash")
                content = content.replace('href="/_favicon', f'href="{base_path}/_favicon')
            # 替换 /upload -> /{base_path}/upload
            if base_path:
                content = content.replace("'/upload'", f"'{base_path}/upload'")
                content = content.replace('"/upload"', f'"{base_path}/upload"')
            # 替换 /viewer -> /{base_path}/viewer
            if base_path:
                content = content.replace("'/viewer", f"'{base_path}/viewer")
                content = content.replace('"/viewer', f'"{base_path}/viewer')
            # 替换 /api -> /{base_path}/api
            if base_path:
                content = content.replace("'/api/", f"'{base_path}/api/")
                content = content.replace('"/api/', f'"{base_path}/api/')
            # 替换 _dash-config 中的 url_base_pathname 和 requests_pathname_prefix
            if base_path:
                content = content.replace('"url_base_pathname":null', f'"url_base_pathname":"{base_path}/"')
                content = content.replace('"url_base_pathname":"/"', f'"url_base_pathname":"{base_path}/"')
                # 处理 requests_pathname_prefix（兼容 unicode 转义和非转义两种格式）
                content = content.replace('"requests_pathname_prefix":"\\u002f"', f'"requests_pathname_prefix":"{base_path}/"')
                content = content.replace('"requests_pathname_prefix":"/"', f'"requests_pathname_prefix":"{base_path}/"')

            # 注入访问计数器
            if app_name and app_name in visit_counts:
                visit_info = get_visit_info(app_name)
                counter_html = f'<p style="color:#999;font-size:14px;text-align:center;margin-top:10px;position:fixed;bottom:10px;left:0;right:0;z-index:9999;background:rgba(255,255,255,0.8);padding:5px;">This is the {visit_info["app_visit"]}th visit for current function. ({visit_info["total_visits"]} visits in total)</p>'
                # 注入到 </body> 之前
                if '</body>' in content:
                    content = content.replace('</body>', counter_html + '</body>')
                elif '</html>' in content:
                    content = content.replace('</html>', counter_html + '</html>')

            resp._content = content.encode('utf-8')

        # 过滤代理服务器的响应头
        headers = {
            k: v for k, v in resp.headers.items()
            if k.lower() not in ('transfer-encoding', 'connection', 'keep-alive')
        }

        return Response(resp.content, resp.status_code, headers.items())
    except requests.exceptions.Timeout:
        return Response("Service timeout", 504)
    except requests.exceptions.ConnectionError:
        return Response("Service unavailable", 503)
    except Exception as e:
        return Response(f"Proxy error: {str(e)}", 500)


# ==================== 路由 ====================

@app.route('/')
def index():
    # 增加首页访问计数
    total = get_total_visits()
    return render_template_string(HTML_TEMPLATE, total_visits=total)


@app.route('/layout-designer/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/layout-designer/<path:path>', methods=['GET', 'POST'])
def layout_designer(path):
    visit_counts['layout-designer'] += 1
    return proxy_request(DASH_PORT, path, '/layout-designer', 'layout-designer')


@app.route('/efd-analyzer/', defaults={'path': ''}, methods=['GET', 'POST'])
@app.route('/efd-analyzer/<path:path>', methods=['GET', 'POST'])
def efd_analyzer(path):
    visit_counts['efd-analyzer'] += 1
    return proxy_request(FASTAPI_PORT, path, '/efd-analyzer', 'efd-analyzer')


# ==================== WharfUtil 路由 ====================

@app.route('/wharf-util')
def wharf_util():
    """Wharf Utilization 主页"""
    visit_counts['wharf-util'] += 1
    visit_info = get_visit_info('wharf-util')
    uploaded_file = session.get('uploaded_filename', '')
    return render_template_string(WHARF_TEMPLATE, uploaded_file=uploaded_file, **visit_info)


@app.route('/wharf-util/upload', methods=['POST'])
def wharf_util_upload():
    """处理文件上传"""
    import uuid
    import shutil

    if 'file' not in request.files:
        return "No file uploaded", 400

    file = request.files['file']
    if file.filename == '':
        return "No file selected", 400

    if file and file.filename.endswith('.json'):
        # 保存上传的文件到临时目录
        temp_dir = WHARF_TOOLKIT_DIR / 'temp_uploads'
        temp_dir.mkdir(exist_ok=True)

        # 生成唯一文件名
        unique_filename = f"{uuid.uuid4().hex}_{file.filename}"
        temp_path = temp_dir / unique_filename
        file.save(temp_path)

        # 保存文件名到 session
        session['uploaded_filepath'] = str(temp_path)
        session['uploaded_filename'] = file.filename

    return redirect('/wharf-util')


@app.route('/wharf-util/chart/<chart_name>')
def wharf_util_chart(chart_name):
    """动态生成 Wharf 图表"""
    import matplotlib
    matplotlib.use('Agg')  # 使用非交互式后端
    import matplotlib.pyplot as plt
    import matplotlib.patches as mpatches
    import json

    WHARF_LENGTH = 3764

    # 必须使用上传的文件
    json_file = None

    # 检查是否有上传的文件
    uploaded_path = session.get('uploaded_filepath')
    if uploaded_path:
        json_file = Path(uploaded_path)
        if not json_file.exists():
            json_file = None

    if json_file is None:
        return "Please upload a JSON data file first", 404

    # 加载数据
    with open(json_file, 'r', encoding='utf-8') as f:
        events = json.load(f)

    # 确定码头名称
    wharf_name = 'wharf_N' if chart_name.lower() in ('n', 'north') else 'wharf_S'

    # 建立 vessel 到 wharf 的映射
    vessel_wharf_map = {}
    for event in events:
        if event.get('eventName') == 'OnStart':
            vessel_wharf_map[event['vesselId']] = event.get('wharf')

    # 为 OnReadyToDepart 事件添加 wharf 字段
    for event in events:
        if event.get('eventName') == 'OnReadyToDepart':
            vessel_id = event.get('vesselId')
            if vessel_id in vessel_wharf_map:
                event['wharf'] = vessel_wharf_map[vessel_id]

    # 获取船只停泊区间
    events_sorted = sorted(events, key=lambda x: x['time'])
    vessel_data = {}

    for event in events_sorted:
        event_name = event.get('eventName')
        vessel_id = event['vesselId']
        wharf = event.get('wharf')
        if wharf is None and vessel_id in vessel_wharf_map:
            wharf = vessel_wharf_map[vessel_id]
        if wharf != wharf_name:
            continue

        if vessel_id not in vessel_data:
            vessel_data[vessel_id] = {}

        if event_name == 'OnStart':
            vessel_data[vessel_id]['start_time'] = event['time']
            vessel_data[vessel_id]['wharfmark_start'] = event['wharfmark_start']
            vessel_data[vessel_id]['wharfmark_end'] = event['wharfmark_end']
        elif event_name == 'OnReadyToDepart':
            vessel_data[vessel_id]['end_time'] = event['time']

    intervals = []
    for vessel_id, data in vessel_data.items():
        if 'start_time' in data:
            intervals.append({
                'vessel_id': vessel_id,
                'start_time': data['start_time'],
                'end_time': data.get('end_time'),
                'wharfmark_start': data['wharfmark_start'],
                'wharfmark_end': data['wharfmark_end']
            })

    if not intervals:
        return "No data for this wharf", 404

    # 获取时间范围
    all_times = []
    for iv in intervals:
        all_times.append(iv['start_time'])
        if iv['end_time'] is not None:
            all_times.append(iv['end_time'])
    time_min = min(all_times)
    time_max = max(all_times)

    # 绘制图表
    fig, ax = plt.subplots(figsize=(12, 10))
    ax.set_xlim(0, WHARF_LENGTH)
    ax.set_ylim(time_max, time_min)
    ax.set_xlabel('Position along wharf (wharfmark)', fontsize=12)
    ax.set_ylabel('Time', fontsize=12)
    ax.set_title(f'{wharf_name} Occupancy Chart', fontsize=14)

    colors = plt.cm.tab20(range(len(intervals)))
    for i, iv in enumerate(intervals):
        x = iv['wharfmark_start']
        y_top = iv['start_time']
        width = iv['wharfmark_end'] - iv['wharfmark_start']
        y_bottom = iv['end_time'] if iv['end_time'] is not None else time_max
        height = y_bottom - y_top

        rect = mpatches.Rectangle(
            (x, y_top), width, height,
            linewidth=1, edgecolor='black', facecolor=colors[i], alpha=0.7
        )
        ax.add_patch(rect)
        ax.text(x + width/2, y_top + height/2, iv['vessel_id'],
                ha='center', va='center', fontsize=6, fontweight='bold')

    ax.grid(True, alpha=0.3)
    plt.tight_layout()

    # 输出到内存
    buf = io.BytesIO()
    plt.savefig(buf, format='png', dpi=150)
    plt.close()
    buf.seek(0)

    return send_file(buf, mimetype='image/png')


@app.route('/wharf-util/download')
def wharf_util_download():
    """下载示例数据文件"""
    json_file = WHARF_TOOLKIT_DIR / "event_vessel_depart_40_hm.json"
    if not json_file.exists():
        return "Example data file not found", 404
    return send_file(json_file, as_attachment=True, download_name='event_vessel_depart_40_hm.json')


# ==================== 子进程管理 ====================

def start_subprocess(script_path, port, name, cwd=None):
    """启动子进程"""
    env = os.environ.copy()
    env['PORT'] = str(port)

    proc = subprocess.Popen(
        [sys.executable, str(script_path)],
        env=env,
        cwd=str(cwd) if cwd else None,
        stdout=sys.stdout,
        stderr=sys.stderr,
    )
    subprocesses.append(proc)
    print(f"[{name}] Started on port {port}, PID: {proc.pid}", flush=True)
    return proc


def _wait_for_port(port, timeout=30):
    """轮询等待端口就绪"""
    import socket
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=1):
                return True
        except OSError:
            time.sleep(0.5)
    return False


def start_backend_services():
    """启动后端服务"""
    print("Starting backend services...", flush=True)

    # 启动 LayoutDesigner (Dash)
    dash_script = LAYOUT_DESIGNER_DIR / "03_DrawPathCombined.py"
    if dash_script.exists():
        # Dash 运行在 / ，由代理负责路径前缀重写
        dash_env = {**os.environ, 'PORT': str(DASH_PORT)}
        proc = subprocess.Popen(
            [sys.executable, str(dash_script)],
            env=dash_env,
            cwd=str(LAYOUT_DESIGNER_DIR),
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        subprocesses.append(proc)
        print(f"[LayoutDesigner] Started on port {DASH_PORT}, PID: {proc.pid}", flush=True)
    else:
        print(f"[LayoutDesigner] Script not found: {dash_script}", flush=True)

    # 启动 EFD-Analyzer (FastAPI) - 需要使用 -m 模块方式运行
    if (EFD_ANALYZER_DIR / "app").exists():
        # 使用 python -m app.main 从 EFD-Analyzer 目录运行
        proc = subprocess.Popen(
            [sys.executable, "-m", "app.main"],
            env={**os.environ, 'PORT': str(FASTAPI_PORT)},
            cwd=str(EFD_ANALYZER_DIR),
            stdout=sys.stdout,
            stderr=sys.stderr,
        )
        subprocesses.append(proc)
        print(f"[EFD-Analyzer] Started on port {FASTAPI_PORT}, PID: {proc.pid}", flush=True)
    else:
        print(f"[EFD-Analyzer] Directory not found: {EFD_ANALYZER_DIR / 'app'}", flush=True)

    # 轮询等待服务就绪（最长30秒）
    for name, port in [("LayoutDesigner", DASH_PORT), ("EFD-Analyzer", FASTAPI_PORT)]:
        if _wait_for_port(port):
            print(f"[{name}] Ready on port {port}", flush=True)
        else:
            print(f"[{name}] WARNING: not ready after 30s on port {port}", flush=True)

    print("Backend services started.", flush=True)


def stop_subprocesses():
    """停止所有子进程"""
    print("Stopping backend services...")
    for proc in subprocesses:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception as e:
            print(f"Error stopping process: {e}")
            try:
                proc.kill()
            except:
                pass


# ==================== 启动 ====================

# gunicorn 用 `gunicorn app:app` 导入时也需要启动子进程
# 用 _services_started 标志防止重复启动（gunicorn 多 worker 场景由 --preload 控制）
_services_started = False

def _ensure_backend_services():
    global _services_started
    if not _services_started:
        _services_started = True
        start_backend_services()
        import atexit
        atexit.register(stop_subprocesses)

# 模块被导入时即启动后端服务（兼容 gunicorn）
_ensure_backend_services()

if __name__ == '__main__':
    # 注册信号处理
    def signal_handler(sig, frame):
        stop_subprocesses()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # 启动 Flask 应用
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting TerminalToolkit Portal on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
