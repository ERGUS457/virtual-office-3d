import http.server
import socketserver
import json
import urllib.request
import os
import sys
from concurrent.futures import ThreadPoolExecutor

PORT = 3333
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

ROUTER_URL = "http://localhost:20128/v1/chat/completions"
ROUTER_KEY = "sk-0900c4ba0ad55579-ohgl0d-7ddf1c78"

def call_9router(system_prompt, user_prompt, model="levantry"):
    try:
        payload = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Instruksi: {user_prompt}\nJawab ringkas dalam 1-2 kalimat Bahasa Indonesia:"}
            ],
            "temperature": 0.7,
            "max_tokens": 120
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
        with urllib.request.urlopen(req, timeout=10) as response:
            res_data = json.loads(response.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        print(f"[9Router Error]: {e}", file=sys.stderr)
        return None

def get_antigravity_response(prompt):
    return call_9router(
        "Anda adalah Antigravity, Project Lead / AI Coordinator di Levantry HQ. Anda sedang memimpin sprint website UMKM Sambas bersama Hermes (Frontend) dan OpenCode (Backend). Berikan arahan koordinasi tugas singkat kepada tim dalam 1-2 kalimat Bahasa Indonesia yang ramah, profesional, dan tegas.",
        prompt
    ) or f"Instruksi diterima: '{prompt}'. Saya koordinasikan sprint ini bersama Hermes dan OpenCode."

def get_hermes_response(prompt):
    return call_9router(
        "Anda adalah Hermes, Frontend & UI/UX Specialist AI di Levantry HQ. Berikan solusi desain antarmuka, layout responsif, atau komponen frontend untuk tugas ini dalam 1-2 kalimat Bahasa Indonesia yang jelas.",
        prompt
    ) or "Komponen UI responsif dan tombol checkout WhatsApp siap saya implementasikan."

def get_opencode_response(prompt):
    return call_9router(
        "Anda adalah OpenCode, Backend Engineer & Database Architect di Levantry HQ. Berikan tanggapan teknis mengenai API, struktur database, atau optimasi server untuk instruksi ini dalam 1-2 kalimat Bahasa Indonesia yang jelas.",
        prompt
    ) or "API endpoint dan database JSON sudah dioptimasi, latensi server aman di bawah 15ms."

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

                # Run all 3 agents concurrently in parallel threads (Super Fast!)
                with ThreadPoolExecutor(max_workers=3) as executor:
                    f_lead = executor.submit(get_antigravity_response, prompt)
                    f_front = executor.submit(get_hermes_response, prompt)
                    f_back = executor.submit(get_opencode_response, prompt)

                    result = {
                        "antigravity": f_lead.result(),
                        "hermes": f_front.result(),
                        "opencode": f_back.result()
                    }

                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(json.dumps({"status": "ok", "data": result}).encode("utf-8"))
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
        print(f"Levantry 3D Virtual Office Native Server running at http://localhost:{PORT}")
        httpd.serve_forever()
