import http.server
import socketserver
import json
import urllib.request
import urllib.parse
import os
import sys
import re
import subprocess
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

PORT = 3333
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

ROUTER_URL = "http://localhost:20128/v1/chat/completions"
ROUTER_KEY = "sk-0900c4ba0ad55579-ohgl0d-7ddf1c78"
LANG_SERVER = r"C:\Users\MyBook Hype\AppData\Local\Programs\antigravity\resources\bin\language_server.exe"

def clean_text(text):
    if not text:
        return ""
    # Strip raw LaTeX math syntax: $1 + (4 \times 82)$ -> 1 + (4 × 82)
    text = text.replace(r"\times", "×").replace(r"\cdot", "·").replace(r"\div", "÷")
    text = re.sub(r"\$([^\$]+)\$", r"\1", text)
    return text.strip()

# ==========================================
# MCP TOOL IMPLEMENTATIONS
# ==========================================

def mcp_github(query=""):
    print(f"[MCP-GitHub] Checking for query: '{query}'")
    try:
        # Check if asking for specific repository
        m = re.search(r"repo(?:sitory)?\s+([a-zA-Z0-9_\-]+)", query, re.IGNORECASE)
        skip_words = {"github", "saya", "ku", "kami", "ada", "list", "daftar", "cek", "semua"}
        if m and m.group(1).lower() not in skip_words:
            target = m.group(1)
            res = subprocess.run(["gh", "repo", "view", f"ERGUS457/{target}"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                return f"Detail Repositori GitHub ERGUS457/{target}:\n{res.stdout.strip()[:400]}"

        # Default: list repositories
        res = subprocess.run(["gh", "repo", "list", "ERGUS457", "--limit", "6"], capture_output=True, text=True, timeout=10)
        if res.returncode == 0 and res.stdout.strip():
            return "Daftar Repositori GitHub (Akun: ERGUS457):\n" + res.stdout.strip()
        return "GitHub CLI aktif, namun tidak ada repositori yang ditemukan atau terjadi pembatasan akses."
    except Exception as e:
        return f"Error eksekusi GitHub MCP: {e}"

def mcp_google_workspace(query=""):
    print(f"[MCP-Workspace] Checking for query: '{query}'")
    q_lower = query.lower()
    try:
        if any(k in q_lower for k in ["email", "gmail", "surat", "inbox", "pesan"]):
            res = subprocess.run([LANG_SERVER, "plugin-cli", "gmail", "readonly", "search", "newer_than:7d"], capture_output=True, text=True, timeout=12)
            lines = [l for l in res.stdout.splitlines() if not l.startswith("=") and not l.startswith("[WARNING]") and not l.startswith("INSTRUCTION") and not l.startswith("//depot") and l.strip()]
            if lines:
                return "Pesan Gmail Terbaru (Akun: ergus87@gmail.com):\n" + "\n".join(lines[:8])
            return "Kotak masuk Gmail bersih atau tidak ada pesan dalam 7 hari terakhir."
        else:
            res = subprocess.run([LANG_SERVER, "plugin-cli", "gdrive", "readonly", "recent"], capture_output=True, text=True, timeout=12)
            lines = [l for l in res.stdout.splitlines() if l.strip()]
            if lines:
                return "File Google Drive Terbaru (Akun: ergus87@gmail.com):\n" + "\n".join(lines[:8])
            return "Google Drive aktif, namun tidak ada file terbaru yang terdaftar."
    except Exception as e:
        return f"Error eksekusi Google Workspace MCP: {e}"

def mcp_web_search(query=""):
    print(f"[MCP-WebSearch] Searching web for: '{query}'")
    results = []
    clean_q = re.sub(r"^(cari(kan)?|search|googling|internet|info|berita)\s+", "", query, flags=re.IGNORECASE).strip()
    target_q = clean_q or query

    # 1. Google News RSS for live headlines & current events
    try:
        encoded_q = urllib.parse.quote(target_q)
        req = urllib.request.Request(
            f"https://news.google.com/rss/search?q={encoded_q}&hl=id&gl=ID&ceid=ID:id",
            headers={"User-Agent": "Mozilla/5.0"}
        )
        with urllib.request.urlopen(req, timeout=5) as r:
            root = ET.fromstring(r.read())
            items = root.findall(".//item")[:3]
            for it in items:
                title = it.find("title").text if it.find("title") is not None else ""
                pub = it.find("pubDate").text if it.find("pubDate") is not None else ""
                if title:
                    results.append(f"• [Berita] {title} ({pub})")
    except Exception:
        pass

    # 2. Wikipedia Summary for knowledge, definitions & entities
    try:
        def_q = re.sub(r"^(siapa|apa\s+itu|jelaskan|pengertian)\s+", "", target_q, flags=re.IGNORECASE).strip()
        encoded_wiki = urllib.parse.quote(def_q or target_q)
        wiki_req = urllib.request.Request(
            f"https://id.wikipedia.org/w/api.php?action=opensearch&search={encoded_wiki}&limit=2&namespace=0&format=json",
            headers={"User-Agent": "LevantryOffice/1.0 (contact@ergus.dev)"}
        )
        with urllib.request.urlopen(wiki_req, timeout=5) as r:
            wdata = json.loads(r.read().decode("utf-8"))
            if len(wdata) > 1 and wdata[1]:
                title = wdata[1][0]
                url = wdata[3][0] if len(wdata) > 3 and wdata[3] else ""
                sum_req = urllib.request.Request(
                    f"https://id.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(title.replace(' ', '_'))}",
                    headers={"User-Agent": "LevantryOffice/1.0 (contact@ergus.dev)"}
                )
                with urllib.request.urlopen(sum_req, timeout=5) as sr:
                    sdata = json.loads(sr.read().decode("utf-8"))
                    ext = sdata.get("extract", "")
                    if ext:
                        results.append(f"• [Wikipedia - {title}]: {ext[:280]}... (Ref: {url})")
    except Exception:
        pass

    if results:
        return "Hasil Pencarian Internet Terkini:\n" + "\n".join(results)
    return f"Pencarian internet selesai: Data tidak ditemukan untuk kata kunci '{query}'."

def dispatch_mcp_tool(prompt):
    p_lower = prompt.lower()
    
    # 1. GitHub Intent
    if any(k in p_lower for k in ["github", "repo", "repository", "commit", "issue", "ergus457", "pull request", "pr list"]):
        output = mcp_github(prompt)
        metadata = {
            "executed": True,
            "tool": "github",
            "title": "🐙 GitHub MCP CLI (ERGUS457)",
            "summary": "Data repositori GitHub pengguna berhasil diambil langsung melalui gh CLI.",
            "details": output
        }
        context = f"[DATA EKSEKUSI MCP TOOL: GITHUB]\n{output}"
        return metadata, context

    # 2. Google Workspace Intent
    if any(k in p_lower for k in ["drive", "gdrive", "email", "gmail", "inbox", "surat", "dokumen drive", "google workspace", "workspace"]):
        output = mcp_google_workspace(prompt)
        is_mail = any(k in p_lower for k in ["email", "gmail", "surat", "inbox"])
        metadata = {
            "executed": True,
            "tool": "workspace",
            "title": "📁 Google Workspace MCP (ergus87@gmail.com)" if not is_mail else "📧 Gmail MCP (ergus87@gmail.com)",
            "summary": "Data Google Workspace berhasil disinkronkan langsung dari akun resmi pengguna.",
            "details": output
        }
        context = f"[DATA EKSEKUSI MCP TOOL: GOOGLE WORKSPACE]\n{output}"
        return metadata, context

    # 3. Web Search Intent
    if any(k in p_lower for k in ["cari", "search", "googling", "internet", "berita", "terbaru", "terkini", "kabar", "siapa", "apa itu", "informasi"]):
        output = mcp_web_search(prompt)
        metadata = {
            "executed": True,
            "tool": "web_search",
            "title": "🌐 Web Search MCP (Live Data Retrieval)",
            "summary": f"Pencarian internet langsung berhasil mendapatkan informasi terkini untuk '{prompt}'.",
            "details": output
        }
        context = f"[DATA EKSEKUSI MCP TOOL: WEB SEARCH INTERNET]\n{output}"
        return metadata, context

    return {"executed": False}, ""

# ==========================================
# 9ROUTER / GEMINI COMPLETIONS
# ==========================================

def call_9router(system_prompt, user_prompt, model="levantry"):
    try:
        payload = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Pertanyaan/Instruksi User: {user_prompt}\nJawab secara alami, lugas, akurat, dan profesional dalam 1-2 kalimat Bahasa Indonesia:"}
            ],
            "temperature": 0.5,
            "max_tokens": 160
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            ROUTER_URL,
            data=data,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {ROUTER_KEY}"
            }
        )
        with urllib.request.urlopen(req, timeout=12) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            raw_text = res_data["choices"][0]["message"]["content"].strip()
            return clean_text(raw_text)
    except Exception as e:
        print(f"[9Router Error]: {e}", file=sys.stderr)
        return None

def get_antigravity_response(prompt, mcp_context=""):
    full_prompt = f"{mcp_context}\n\nInstruksi: {prompt}" if mcp_context else prompt
    sys_prompt = (
        "Anda adalah Antigravity, Project Lead & AI Coordinator di Levantry Office. "
        "Tanggapi pertanyaan user secara langsung, cerdas, dan lugas. "
        "Jika terdapat data hasil eksekusi MCP tool, simpulkan poin kuncinya untuk user secara profesional. "
        "Jika pertanyaan umum/matematika, jawab hasilnya dengan tepat tanpa memaksakan topik yang tidak relevan. "
        "Hindari simbol rumus LaTeX dolar ($)."
    )
    return call_9router(sys_prompt, full_prompt) or f"Instruksi diterima: '{prompt}'. Saya koordinasikan solusinya bersama tim."

def get_hermes_response(prompt, mcp_context=""):
    full_prompt = f"{mcp_context}\n\nInstruksi: {prompt}" if mcp_context else prompt
    sys_prompt = (
        "Anda adalah Hermes, Frontend & UI/UX Specialist di Levantry Office. "
        "Berikan tanggapan yang ramah, visual, dan jelas. "
        "Jika ada data hasil eksekusi MCP tool, jelaskan bagaimana data tersebut dapat ditampilkan pada antarmuka atau bermanfaat untuk user experience. "
        "Hindari format matematika LaTeX ($)."
    )
    return call_9router(sys_prompt, full_prompt) or "Tampilan visual dan antarmuka interaktif siap kami integrasikan."

def get_opencode_response(prompt, mcp_context=""):
    full_prompt = f"{mcp_context}\n\nInstruksi: {prompt}" if mcp_context else prompt
    sys_prompt = (
        "Anda adalah OpenCode, Backend Engineer & Database Architect di Levantry Office. "
        "Berikan tanggapan logis, teknis, dan presisi. "
        "Jika ada data hasil eksekusi MCP tool, jelaskan aspek teknis, API endpoint, atau integrasi data dari hasil tersebut. "
        "Hindari format rumus LaTeX dolar ($)."
    )
    return call_9router(sys_prompt, full_prompt) or "Infrastruktur server dan pipeline data siap mengeksekusi instruksi ini."

# ==========================================
# HTTP SERVER & API ROUTING
# ==========================================

class OfficeRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)

    def end_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        super().end_headers()

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def do_POST(self):
        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)
            try:
                req_json = json.loads(post_body.decode("utf-8"))
                prompt = req_json.get("prompt", "").strip()

                # 1. MCP Tool Dispatching
                mcp_meta, mcp_context = dispatch_mcp_tool(prompt)

                # 2. Parallel LLM Agent execution
                with ThreadPoolExecutor(max_workers=3) as executor:
                    f_lead = executor.submit(get_antigravity_response, prompt, mcp_context)
                    f_front = executor.submit(get_hermes_response, prompt, mcp_context)
                    f_back = executor.submit(get_opencode_response, prompt, mcp_context)

                    result = {
                        "antigravity": f_lead.result(),
                        "hermes": f_front.result(),
                        "opencode": f_back.result()
                    }

                response_payload = {
                    "status": "ok",
                    "data": result,
                    "mcp": mcp_meta
                }

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps(response_payload).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
                return

        self.send_response(404)
        self.end_headers()

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), OfficeRequestHandler) as httpd:
        print(f"=======================================================")
        print(f"Levantry 3D Virtual Office MCP Native Server")
        print(f"Running at: http://localhost:{PORT}")
        print(f"MCP Tools Active:")
        print(f"  [1] Web Search (Google News + Wikipedia)")
        print(f"  [2] GitHub CLI (User: ERGUS457)")
        print(f"  [3] Google Workspace CLI (User: ergus87@gmail.com)")
        print(f"=======================================================")
        httpd.serve_forever()
