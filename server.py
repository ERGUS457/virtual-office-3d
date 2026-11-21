import http.server
import socketserver
import json
import urllib.request
import os
import sys
import re
from concurrent.futures import ThreadPoolExecutor

PORT = 3333
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

ROUTER_URL = "http://localhost:20128/v1/chat/completions"
ROUTER_KEY = "sk-0900c4ba0ad55579-ohgl0d-7ddf1c78"

def clean_text(text):
    if not text:
        return ""
    # Strip raw LaTeX math syntax: $1 + (4 \times 82)$ -> 1 + (4 × 82)
    text = text.replace(r"\times", "×").replace(r"\cdot", "·").replace(r"\div", "÷")
    text = re.sub(r"\$([^\$]+)\$", r"\1", text)
    return text.strip()

def call_9router(system_prompt, user_prompt, model="levantry"):
    try:
        payload = {
            "model": model,
            "stream": False,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Pertanyaan/Instruksi: {user_prompt}\nJawab secara alami, lugas, dan akurat dalam 1-2 kalimat Bahasa Indonesia:"}
            ],
            "temperature": 0.5,
            "max_tokens": 140
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
            raw_text = res_data["choices"][0]["message"]["content"].strip()
            return clean_text(raw_text)
    except Exception as e:
        print(f"[9Router Error]: {e}", file=sys.stderr)
        return None

def get_antigravity_response(prompt):
    return call_9router(
        "Anda adalah Antigravity, Project Lead & AI Coordinator di Levantry. Tanggapi pertanyaan user secara langsung, cerdas, dan lugas. Jika pertanyaan umum/matematika, jawab hasilnya dengan tepat. Jika tugas proyek, koordinasikan langkah kerja dengan jelas tanpa memaksa topik yang tidak relevan. Jangan gunakan sintaks LaTeX atau simbol rumit.",
        prompt
    ) or f"Instruksi diterima: '{prompt}'. Saya koordinasikan solusinya bersama tim."

def get_hermes_response(prompt):
    return call_9router(
        "Anda adalah Hermes, Frontend & UI/UX Specialist di Levantry. Berikan jawaban yang ramah, visual, dan jelas. Jika pertanyaan umum/matematika, jelaskan dengan alur logika yang mudah dipahami. Hindari penggunaan format LaTeX simbol dolar.",
        prompt
    ) or "Solusi antarmuka dan pengalaman pengguna siap saya susun."

def get_opencode_response(prompt):
    return call_9router(
        "Anda adalah OpenCode, Backend Engineer & Database Architect di Levantry. Berikan jawaban logis, teknis, dan presisi. Jika pertanyaan umum/matematika, berikan verifikasi perhitungan dengan jelas. Tulis angka dan rumus secara teks biasa (jangan pakai $ atau LaTeX).",
        prompt
    ) or "Sistem komputasi dan arsitektur data siap memproses instruksi ini."

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
