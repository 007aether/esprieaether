import os
import json
import tempfile
import uuid
from pathlib import Path
from typing import List

from .core import convert_file, get_file_info, read_file, create_file, detect_format
from .utils import FORMATS, format_size

try:
    from fastapi import FastAPI, UploadFile, File, Form, HTTPException
    from fastapi.responses import HTMLResponse, FileResponse, JSONResponse
    import uvicorn
except ImportError:
    FastAPI = None
    uvicorn = None

app = FastAPI(title="Atulya Converter")

TEMP_DIR = Path(tempfile.gettempdir()) / "atulya_webui"
TEMP_DIR.mkdir(exist_ok=True)

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Atulya Converter</title>
<style>
*{margin:0;padding:0;box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}
body{background:#0d1117;color:#c9d1d9;min-height:100vh}
.header{background:#161b22;border-bottom:1px solid #30363d;padding:16px 24px}
.header h1{font-size:20px;color:#58a6ff}
.header span{color:#8b949e;font-size:14px}
.container{max-width:960px;margin:0 auto;padding:24px}
.card{background:#161b22;border:1px solid #30363d;border-radius:8px;padding:24px;margin-bottom:16px}
.card h2{font-size:16px;color:#f0f6fc;margin-bottom:16px}
.drop-zone{border:2px dashed #30363d;border-radius:8px;padding:40px;text-align:center;cursor:pointer;transition:.2s}
.drop-zone:hover,.drop-zone.dragover{border-color:#58a6ff;background:#0d1117}
.drop-zone svg{width:48px;height:48px;fill:#58a6ff;margin-bottom:12px}
.drop-zone p{color:#8b949e;font-size:14px}
.drop-zone .browse{color:#58a6ff;text-decoration:underline;cursor:pointer}
.form-row{display:flex;gap:12px;margin:16px 0;flex-wrap:wrap}
.form-row select,.form-row input,.form-row button{padding:8px 12px;border-radius:6px;border:1px solid #30363d;background:#0d1117;color:#c9d1d9;font-size:14px}
.form-row select{flex:1;min-width:120px}
.form-row button{background:#238636;border-color:#2ea043;cursor:pointer;font-weight:600}
.form-row button:hover{background:#2ea043}
.btn-secondary{background:#21262d!important;border-color:#30363d!important}
.btn-secondary:hover{background:#30363d!important}
#output{margin-top:16px}
.preview-box{background:#0d1117;border:1px solid #30363d;border-radius:6px;padding:16px;margin-top:12px;max-height:400px;overflow:auto;white-space:pre-wrap;font-family:monospace;font-size:13px}
.file-info{display:grid;grid-template-columns:auto 1fr;gap:4px 16px;font-size:13px}
.file-info dt{color:#8b949e}
.file-info dd{color:#c9d1d9}
.progress{height:4px;background:#30363d;border-radius:2px;overflow:hidden;margin-top:12px;display:none}
.progress-bar{height:100%;background:#58a6ff;width:0;transition:width .3s}
.file-list{margin-top:12px}
.file-item{display:flex;justify-content:space-between;padding:8px 12px;background:#0d1117;border:1px solid #30363d;border-radius:4px;margin-bottom:4px;font-size:13px}
.tabs{display:flex;gap:4px;margin-bottom:16px}
.tab{padding:8px 16px;border-radius:6px 6px 0 0;cursor:pointer;background:#0d1117;border:1px solid #30363d;border-bottom:none;font-size:13px;color:#8b949e}
.tab.active{background:#161b22;color:#f0f6fc}
.tab-content{display:none}
.tab-content.active{display:block}
.success{color:#3fb950}
.error{color:#f85149}
a{color:#58a6ff}
</style>
</head>
<body>
<div class="header"><h1>Atulya Converter <span>v0.1.0</span></h1></div>
<div class="container">
<div class="tabs">
<div class="tab active" onclick="switchTab('convert')">Convert</div>
<div class="tab" onclick="switchTab('info')">File Info</div>
<div class="tab" onclick="switchTab('create')">Create File</div>
<div class="tab" onclick="switchTab('batch')">Batch</div>
</div>

<div id="tab-convert" class="tab-content active">
<div class="card">
<div class="drop-zone" id="dropZone" onclick="document.getElementById('fileInput').click()">
<svg viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8l-6-6zM6 20V4h7v5h5v11H6z"/></svg>
<p>Drag & drop a file here or <span class="browse">browse</span></p>
</div>
<input type="file" id="fileInput" style="display:none" onchange="handleFile(this.files[0])">
<div class="form-row">
<select id="toFormat"><option value="">Detect automatically</option></select>
<button onclick="convertFile()">Convert</button>
<button class="btn-secondary" onclick="downloadResult()" id="downloadBtn" style="display:none">Download</button>
</div>
<div id="output"></div>
<div class="progress" id="progress"><div class="progress-bar" id="progressBar"></div></div>
</div>
</div>

<div id="tab-info" class="tab-content">
<div class="card">
<div class="drop-zone" onclick="document.getElementById('infoInput').click()" style="padding:20px">
<p>Drop a file for details <span class="browse">browse</span></p>
</div>
<input type="file" id="infoInput" style="display:none" onchange="getInfo(this.files[0])">
<div id="infoOutput"></div>
</div>
</div>

<div id="tab-create" class="tab-content">
<div class="card">
<div class="form-row">
<select id="createFormat"></select>
<input type="text" id="createName" placeholder="filename.ext" value="sample">
<button onclick="createFile()">Create</button>
</div>
<div id="createOutput"></div>
</div>
</div>

<div id="tab-batch" class="tab-content">
<div class="card">
<p style="color:#8b949e;margin-bottom:12px">Select multiple files to batch convert</p>
<input type="file" id="batchInput" multiple onchange="batchFiles(this.files)" style="margin-bottom:12px">
<div class="form-row">
<select id="batchFormat"></select>
<button onclick="batchConvert()">Convert All</button>
</div>
<div id="batchOutput"></div>
<div class="file-list" id="batchList"></div>
</div>
</div>
</div>

<script>
let currentFile = null;
let currentResult = null;

async function switchTab(name) {
  document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
  document.querySelector(`.tab[onclick*="${name}"]`).classList.add('active');
  document.getElementById(`tab-${name}`).classList.add('active');
}

function populateFormats() {
  fetch('/api/formats').then(r=>r.json()).then(formats => {
    const sel = ['toFormat','createFormat','batchFormat'];
    sel.forEach(id => {
      const s = document.getElementById(id);
      s.innerHTML = '';
      if(id==='toFormat') s.innerHTML = '<option value="">Auto detect</option>';
      Object.keys(formats).sort().forEach(f => {
        s.innerHTML += `<option value="${f}">.${f}</option>`;
      });
    });
  });
}

function handleFile(file) {
  if(!file) return;
  currentFile = file;
  document.querySelector('#dropZone p').innerHTML = `<strong>${file.name}</strong> (${(file.size/1024).toFixed(1)} KB)`;
  document.getElementById('output').innerHTML = '';
  document.getElementById('downloadBtn').style.display = 'none';
  document.getElementById('progress').style.display = 'block';
}

function convertFile() {
  if(!currentFile) return;
  const form = new FormData();
  form.append('file', currentFile);
  form.append('to_format', document.getElementById('toFormat').value);
  document.getElementById('progressBar').style.width = '50%';
  fetch('/api/convert', {method:'POST',body:form})
    .then(r=>r.json())
    .then(data => {
      document.getElementById('progressBar').style.width = '100%';
      if(data.error) { document.getElementById('output').innerHTML = `<div class="error">${data.error}</div>`; return }
      currentResult = data;
      document.getElementById('output').innerHTML = `<div class="success">Converted! (${data.size})</div>
        <div class="preview-box">${escapeHtml(data.preview || '')}</div>`;
      document.getElementById('downloadBtn').style.display = 'inline-block';
    });
}

function downloadResult() {
  if(!currentResult) return;
  window.location.href = `/api/download/${currentResult.id}`;
}

function getInfo(file) {
  if(!file) return;
  const form = new FormData();
  form.append('file', file);
  fetch('/api/info', {method:'POST',body:form})
    .then(r=>r.json())
    .then(data => {
      let html = '<dl class="file-info">';
      for(const [k,v] of Object.entries(data)) {
        if(typeof v !== 'object') html += `<dt>${k}</dt><dd>${v}</dd>`;
      }
      html += '</dl>';
      document.getElementById('infoOutput').innerHTML = html;
    });
}

function createFile() {
  const fmt = document.getElementById('createFormat').value;
  const name = document.getElementById('createName').value || 'sample';
  fetch(`/api/create/${fmt}/${name}`, {method:'POST'})
    .then(r=>r.json())
    .then(data => {
      document.getElementById('createOutput').innerHTML = data.path ?
        `<div class="success">Created: ${data.path} (${data.size})</div>` :
        `<div class="error">${data.error}</div>`;
    });
}

let batchFilesList = [];

function batchFiles(files) {
  batchFilesList = Array.from(files);
  const list = document.getElementById('batchList');
  list.innerHTML = batchFilesList.map(f => `<div class="file-item"><span>${f.name}</span><span>${(f.size/1024).toFixed(1)} KB</span></div>`).join('');
}

function batchConvert() {
  if(!batchFilesList.length) return;
  const form = new FormData();
  batchFilesList.forEach(f => form.append('files', f));
  form.append('to_format', document.getElementById('batchFormat').value);
  fetch('/api/batch', {method:'POST',body:form})
    .then(r=>r.json())
    .then(results => {
      document.getElementById('batchOutput').innerHTML = results.map(r =>
        `<div class="file-item"><span>${r.name}</span><span class="${r.status}">${r.status}${r.size ? ' ('+r.size+')' : ''}</span></div>`
      ).join('');
    });
}

function escapeHtml(s) { return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;') }

populateFormats();
</script>
</body>
</html>"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return HTML


@app.get("/api/formats")
async def list_formats():
    return {fmt: info["cat"] for fmt, info in FORMATS.items()}


@app.post("/api/convert")
async def api_convert(file: UploadFile = File(...), to_format: str = Form("")):
    input_ext = os.path.splitext(file.filename)[1].lower().lstrip(".")
    sid = uuid.uuid4().hex[:12]
    input_path = TEMP_DIR / f"{sid}_in{os.path.splitext(file.filename)[1]}"

    content = await file.read()
    with open(input_path, "wb") as f:
        f.write(content)

    fmt = to_format or detect_format(str(input_path)) or "txt"
    output_path = TEMP_DIR / f"{sid}_out.{fmt}"

    try:
        size = convert_file(str(input_path), str(output_path))
        result = read_file(str(output_path))
        preview = ""
        if isinstance(result, dict) and "content" in result:
            preview = str(result["content"])[:2000]
        elif isinstance(result, dict) and "data" in result:
            preview = json.dumps(result["data"], indent=2, default=str)[:2000]
        else:
            preview = json.dumps(result, indent=2, default=str)[:2000]

        return JSONResponse({
            "id": sid,
            "size": size,
            "preview": preview,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)
    finally:
        if input_path.exists():
            input_path.unlink()


@app.get("/api/download/{file_id}")
async def api_download(file_id: str):
    for p in TEMP_DIR.glob(f"{file_id}_out.*"):
        return FileResponse(str(p), filename=f"converted{p.suffix}")
    raise HTTPException(404, "File not found")


@app.post("/api/info")
async def api_info(file: UploadFile = File(...)):
    content = await file.read()
    sid = uuid.uuid4().hex[:12]
    ext = os.path.splitext(file.filename)[1] or ".tmp"
    input_path = TEMP_DIR / f"{sid}{ext}"
    with open(input_path, "wb") as f:
        f.write(content)
    try:
        info = get_file_info(str(input_path))
        return info
    finally:
        if input_path.exists():
            input_path.unlink()


@app.post("/api/create/{fmt}/{name}")
async def api_create(fmt: str, name: str):
    output_path = TEMP_DIR / f"{name}.{fmt}"
    try:
        size = create_file(str(output_path))
        return {"path": str(output_path), "size": size}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


@app.post("/api/batch")
async def api_batch(files: List[UploadFile] = File(...), to_format: str = Form("")):
    results = []
    for file in files:
        content = await file.read()
        sid = uuid.uuid4().hex[:12]
        ext = os.path.splitext(file.filename)[1] or ".tmp"
        input_path = TEMP_DIR / f"{sid}_in{ext}"
        with open(input_path, "wb") as f:
            f.write(content)
        try:
            out_fmt = to_format or detect_format(str(input_path)) or "txt"
            output_path = TEMP_DIR / f"{sid}_out.{out_fmt}"
            size = convert_file(str(input_path), str(output_path))
            results.append({"name": f"{os.path.splitext(file.filename)[0]}.{out_fmt}", "status": "ok", "size": size})
        except Exception as e:
            results.append({"name": file.filename, "status": "error", "size": str(e)})
        finally:
            if input_path.exists():
                input_path.unlink()
    return results


@app.get("/api/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


def serve(host="127.0.0.1", port=8080):
    if uvicorn is None:
        print("WebUI requires: pip install atulya-convert[web]")
        print("  Or: pip install fastapi uvicorn python-multipart")
        return
    print(f"Atulya Converter WebUI: http://{host}:{port}")
    uvicorn.run(app, host=host, port=port, log_level="info")
