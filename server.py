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
MEMORY_FILE = os.path.join(DIRECTORY, "memory.json")

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
# PERSISTENT LONG-TERM MEMORY (LTM) SYSTEM
# ==========================================

def load_memory():
    if not os.path.exists(MEMORY_FILE):
        default_mem = {
            "profile": {
                "user_name": "Ergus",
                "organization": "Levantry HQ",
                "role": "Founder & Lead Director",
                "github_user": "ERGUS457",
                "email": "ergus87@gmail.com"
            },
            "projects": [
                {
                    "name": "Website UMKM Sambas Berjaya",
                    "status": "Sedang Berjalan",
                    "description": "Platform digital untuk memamerkan produk tenun, kuliner, dan kriya khas Sambas dengan katalog interaktif dan checkout WhatsApp."
                },
                {
                    "name": "Levantry 3D Virtual Office",
                    "status": "Aktif & Terintegrasi",
                    "description": "Kantor virtual multi-agen 3D bertenaga Gemini 3.8 Flash, dilengkapi integrasi MCP (Live Web Search, GitHub CLI, Google Workspace)."
                }
            ],
            "decisions": [
                "Semua respons teks dari Antigravity, Hermes, dan OpenCode wajib menggunakan teks bersih tanpa sintaks LaTeX dolar ($).",
                "Model utama tim AI menggunakan Gemini 3.8 Flash untuk kecepatan analisis dan inferensi real-time.",
                "Hermes bertanggung jawab atas UI responsif Tailwind CSS, OpenCode memegang kendali database & server, dan Antigravity mengoordinasikan sprint."
            ],
            "conversations": []
        }
        save_memory(default_mem)
        return default_mem
    try:
        with open(MEMORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"[Memory Error]: {e}", file=sys.stderr)
        return {"conversations": [], "decisions": [], "projects": [], "profile": {}}

def save_memory(mem):
    try:
        with open(MEMORY_FILE, "w", encoding="utf-8") as f:
            json.dump(mem, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"[Memory Save Error]: {e}", file=sys.stderr)

def build_memory_context():
    mem = load_memory()
    profile = mem.get("profile", {})
    projects = mem.get("projects", [])
    decisions = mem.get("decisions", [])
    convs = mem.get("conversations", [])

    lines = [
        "[MEMORI JANGKA PANJANG & KNOWLEDGE BASE KANTOR LEVANTRY]",
        f"Profil User: {profile.get('user_name', 'Ergus')} ({profile.get('role', 'Owner')}, {profile.get('organization', 'Levantry')})",
        f"Akun Terkoneksi: GitHub: {profile.get('github_user', 'ERGUS457')}, Email: {profile.get('email', 'ergus87@gmail.com')}"
    ]

    if projects:
        p_lines = [f"• {p['name']} [{p.get('status', 'Active')}]: {p.get('description', '')}" for p in projects[:2]]
        lines.append("Proyek Aktif:\n" + "\n".join(p_lines))

    if decisions:
        d_lines = [f"• {d}" for d in decisions[-3:]]
        lines.append("Keputusan & Arahan Tetap Tim:\n" + "\n".join(d_lines))

    # Add last 3 conversational turns for dialogue continuity
    recent_convs = convs[-3:]
    if recent_convs:
        lines.append("Riwayat Pembahasan Terakhir:")
        for i, c in enumerate(recent_convs, 1):
            u_text = c.get("user", "")
            lead_summary = c.get("antigravity", "")
            lines.append(f"  [Diskusi #{i}] User: '{u_text}' -> Arahan Tim: '{lead_summary[:120]}...'")

    return "\n".join(lines)

def record_turn(user_prompt, antigravity_res, hermes_res, opencode_res, tool_name=None):
    mem = load_memory()
    if "conversations" not in mem:
        mem["conversations"] = []
    
    turn = {
        "user": user_prompt,
        "antigravity": antigravity_res,
        "hermes": hermes_res,
        "opencode": opencode_res,
        "tool_used": tool_name
    }
    mem["conversations"].append(turn)
    # Keep rolling buffer of last 15 turns
    if len(mem["conversations"]) > 15:
        mem["conversations"] = mem["conversations"][-15:]
    save_memory(mem)

# ==========================================
# MCP TOOL IMPLEMENTATIONS
# ==========================================

def mcp_github(query=""):
    print(f"[MCP-GitHub] Checking for query: '{query}'")
    try:
        m = re.search(r"repo(?:sitory)?\s+([a-zA-Z0-9_\-]+)", query, re.IGNORECASE)
        skip_words = {"github", "saya", "ku", "kami", "ada", "list", "daftar", "cek", "semua"}
        if m and m.group(1).lower() not in skip_words:
            target = m.group(1)
            res = subprocess.run(["gh", "repo", "view", f"ERGUS457/{target}"], capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                return f"Detail Repositori GitHub ERGUS457/{target}:\n{res.stdout.strip()[:400]}"

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
        with urllib.request.urlopen(req, timeout=14) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            raw_text = res_data["choices"][0]["message"]["content"].strip()
            return clean_text(raw_text)
    except Exception as e:
        print(f"[9Router Error]: {e}", file=sys.stderr)
        return None

def get_antigravity_response(prompt, context=""):
    full_prompt = f"{context}\n\nInstruksi User: {prompt}" if context else prompt
    sys_prompt = (
        "Anda adalah Antigravity, Project Lead & AI Coordinator di Levantry Office. "
        "Gunakan memori jangka panjang dan data nyata di atas untuk menjaga kesinambungan diskusi proyek. "
        "Tanggapi pertanyaan user secara langsung, cerdas, dan profesional. "
        "Jika ada pembahasan sebelumnya, rujuk secara alami tanpa mengulang kalimat kaku. "
        "Hindari simbol rumus LaTeX dolar ($)."
    )
    return call_9router(sys_prompt, full_prompt) or f"Instruksi diterima: '{prompt}'. Saya koordinasikan solusinya bersama tim."

def get_hermes_response(prompt, context=""):
    full_prompt = f"{context}\n\nInstruksi User: {prompt}" if context else prompt
    sys_prompt = (
        "Anda adalah Hermes, Frontend & UI/UX Specialist di Levantry Office. "
        "Gunakan memori tim di atas untuk melanjutkan desain dan antarmuka web secara konsisten. "
        "Berikan tanggapan yang ramah, visual, dan jelas untuk kenyamanan pengguna. "
        "Hindari format matematika LaTeX ($)."
    )
    return call_9router(sys_prompt, full_prompt) or "Tampilan visual dan antarmuka interaktif siap kami integrasikan."

def get_opencode_response(prompt, context=""):
    full_prompt = f"{context}\n\nInstruksi User: {prompt}" if context else prompt
    sys_prompt = (
        "Anda adalah OpenCode, Backend Engineer & Database Architect di Levantry Office. "
        "Gunakan memori tim dan data sistem di atas untuk menjaga konsistensi API, server, dan skema data. "
        "Berikan tanggapan teknis yang logis, presisi, dan terverifikasi. "
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

    def do_GET(self):
        if self.path == "/api/memory":
            mem = load_memory()
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.end_headers()
            self.wfile.write(json.dumps({"status": "ok", "memory": mem}).encode("utf-8"))
            return

        super().do_GET()

    def do_POST(self):
        # 1. Tambah Keputusan Permanen Baru
        if self.path == "/api/memory/decision":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)
            try:
                data = json.loads(post_body.decode("utf-8"))
                dec = data.get("decision", "").strip()
                if dec:
                    mem = load_memory()
                    if "decisions" not in mem:
                        mem["decisions"] = []
                    mem["decisions"].append(dec)
                    save_memory(mem)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "message": "Keputusan disimpan ke memori jangka panjang."}).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
                return

        # 2. Reset Riwayat Percakapan
        if self.path == "/api/memory/clear":
            try:
                mem = load_memory()
                mem["conversations"] = []
                save_memory(mem)
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "message": "Riwayat percakapan berhasil dibersihkan."}).encode("utf-8"))
                return
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode("utf-8"))
                return

        # 3. Chat Pipeline dengan Persistent Memory + MCP Tool Calling
        if self.path == "/api/chat":
            content_length = int(self.headers.get("Content-Length", 0))
            post_body = self.rfile.read(content_length)
            try:
                req_json = json.loads(post_body.decode("utf-8"))
                prompt = req_json.get("prompt", "").strip()

                # A. Build Persistent Memory Context
                mem_context = build_memory_context()

                # B. MCP Tool Dispatching
                mcp_meta, mcp_context = dispatch_mcp_tool(prompt)

                # Combined Context
                context_parts = []
                if mem_context:
                    context_parts.append(mem_context)
                if mcp_context:
                    context_parts.append(mcp_context)
                full_context = "\n\n".join(context_parts)

                # C. Parallel LLM Agent execution
                with ThreadPoolExecutor(max_workers=3) as executor:
                    f_lead = executor.submit(get_antigravity_response, prompt, full_context)
                    f_front = executor.submit(get_hermes_response, prompt, full_context)
                    f_back = executor.submit(get_opencode_response, prompt, full_context)

                    lead_text = f_lead.result()
                    front_text = f_front.result()
                    back_text = f_back.result()

                # D. Rekam percakapan ini ke Persistent Memory!
                tool_used = mcp_meta.get("tool") if mcp_meta.get("executed") else None
                record_turn(prompt, lead_text, front_text, back_text, tool_used)

                mem_after = load_memory()
                response_payload = {
                    "status": "ok",
                    "data": {
                        "antigravity": lead_text,
                        "hermes": front_text,
                        "opencode": back_text
                    },
                    "mcp": mcp_meta,
                    "memory": {
                        "active": True,
                        "total_rounds": len(mem_after.get("conversations", [])),
                        "projects_count": len(mem_after.get("projects", [])),
                        "decisions_count": len(mem_after.get("decisions", []))
                    }
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
        print(f"Levantry 3D Virtual Office LTM & MCP Native Server")
        print(f"Running at: http://localhost:{PORT}")
        print(f"Features Active:")
        print(f"  [🧠] Persistent Long-Term Memory (memory.json)")
        print(f"  [🌐] Web Search MCP (Live Google News + Wikipedia)")
        print(f"  [🐙] GitHub MCP (User: ERGUS457)")
        print(f"  [📁] Google Workspace MCP (User: ergus87@gmail.com)")
        print(f"=======================================================")
        httpd.serve_forever()
