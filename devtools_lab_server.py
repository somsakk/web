#!/usr/bin/env python3
"""
DevTools Network Lab
=====================
สคริปต์เดียว รันแล้วได้ web server 2 พอร์ต:
  - localhost:8000  = หน้าเว็บหลัก + API endpoints ธรรมดา
  - localhost:8001  = "external API" คนละ origin ไว้สาธิตเรื่อง CORS จริงๆ

วิธีรัน:
    python3 devtools_lab_server.py

แล้วเปิด http://localhost:8000 ใน Chrome, เปิด DevTools (F12) -> แท็บ Network
กดปุ่มต่างๆ ในหน้าเว็บ แล้วดูว่าแต่ละปุ่มไปโผล่ใน Network tab ยังไง

ไม่ต้อง pip install อะไร ใช้แต่ standard library ของ Python
"""

import json
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ---------------------------------------------------------------------------
# หน้าเว็บหลัก (HTML) - มีปุ่มยิง fetch() ไปยัง endpoint ต่างๆ
# ---------------------------------------------------------------------------
HTML_PAGE = """<!DOCTYPE html>
<html lang="th">
<head>
<meta charset="utf-8">
<title>DevTools Network Lab</title>
<style>
  body { font-family: sans-serif; max-width: 900px; margin: 40px auto; padding: 0 16px; line-height: 1.6; }
  h1 { font-size: 22px; }
  section { border: 1px solid #ccc; border-radius: 8px; padding: 16px; margin-bottom: 16px; }
  h2 { font-size: 16px; margin-top: 0; }
  p.hint { color: #555; font-size: 14px; }
  button { padding: 8px 14px; margin: 4px 6px 4px 0; cursor: pointer; }
  pre { background: #f4f4f4; padding: 10px; border-radius: 6px; max-height: 200px; overflow: auto; font-size: 12px; }
</style>
</head>
<body>
<h1>DevTools Network Lab</h1>
<p>เปิด DevTools (F12) แท็บ <b>Network</b> ค้างไว้ก่อนกดปุ่ม แล้วลองคลิก request ที่ขึ้นมาดูแต่ละแท็บ (Headers, Timing, Response, Payload)</p>

<section>
  <h2>1. Status Code ต่างๆ</h2>
  <p class="hint">สังเกตสี status ในตาราง Network และดูเนื้อหาใน Response tab</p>
  <button onclick="call('/api/instant')">200 OK</button>
  <button onclick="call('/api/notfound')">404 Not Found</button>
  <button onclick="call('/api/error')">500 Server Error</button>
  <button onclick="call('/api/redirect')">302 Redirect</button>
</section>

<section>
  <h2>2. ความเร็ว / Timing tab</h2>
  <p class="hint">ลองเทียบ Timing tab ของสองปุ่มนี้ จะเห็น TTFB ต่างกันชัดเจน</p>
  <button onclick="call('/api/instant')">ตอบทันที</button>
  <button onclick="call('/api/slow')">ตอบช้า 2.5 วิ (จำลอง backend ทำงานหนัก)</button>
  <button onclick="call('/api/large')">ไฟล์ใหญ่ ~500KB (ดู Content Download)</button>
</section>

<section>
  <h2>3. Response Headers: Cache-Control</h2>
  <p class="hint">กดปุ่มนี้ 2 ครั้งติดกัน ครั้งที่สองลองดูว่า status เป็น 200 หรือ "(from disk cache)"</p>
  <button onclick="call('/api/cache')">โหลดไฟล์ที่มี Cache-Control</button>
</section>

<section>
  <h2>4. Set-Cookie / Cookie header</h2>
  <p class="hint">กดปุ่มแรกก่อน แล้วดู Response Headers จะเห็น Set-Cookie จากนั้นกดปุ่มสองแล้วดู Request Headers จะเห็น Cookie ถูกแนบไปเอง</p>
  <button onclick="call('/api/set-cookie')">1. รับ Cookie จาก server</button>
  <button onclick="call('/api/instant')">2. ยิง request ปกติ (เช็คว่ามี Cookie แนบไปไหม)</button>
</section>

<section>
  <h2>5. Authorization Header</h2>
  <p class="hint">ปุ่มแรกไม่แนบ token เลยได้ 401 ปุ่มสองแนบ token ปลอมๆ ไปด้วย ลองดู Request Headers เทียบกัน</p>
  <button onclick="call('/api/need-auth')">ไม่แนบ token (จะได้ 401)</button>
  <button onclick="callWithAuth()">แนบ Authorization: Bearer xxx</button>
</section>

<section>
  <h2>6. POST + Payload tab</h2>
  <p class="hint">ดูแท็บ Payload ของ request นี้ จะเห็น JSON body ที่ส่งไป และ Response จะ echo กลับมา</p>
  <button onclick="callPost()">ส่ง POST พร้อม JSON body</button>
</section>

<section>
  <h2>7. CORS (คนละ origin จริงๆ)</h2>
  <p class="hint">สอง endpoint นี้อยู่ที่ port 8001 (คนละ origin กับหน้านี้ที่ port 8000) ปุ่มแรกเซิร์ฟเวอร์อนุญาต CORS เลยสำเร็จ ปุ่มสองไม่อนุญาต จะเห็น error สีแดงใน Console และ request ใน Network tab ที่ตอบกลับมาแต่ browser บล็อกไม่ให้ JS อ่านผล</p>
  <button onclick="call('http://localhost:8001/allowed')">CORS: อนุญาต</button>
  <button onclick="call('http://localhost:8001/blocked')">CORS: ไม่อนุญาต (จะ error)</button>
</section>

<h2>ผลลัพธ์ล่าสุด</h2>
<pre id="out">-- กดปุ่มด้านบนเพื่อเริ่ม --</pre>

<script>
const out = document.getElementById('out');

async function show(promise, label) {
  out.textContent = 'กำลังยิง request: ' + label + ' ...';
  try {
    const res = await promise;
    const text = await res.text();
    out.textContent = label + '\\nStatus: ' + res.status + '\\n\\n' + text.slice(0, 800);
  } catch (err) {
    out.textContent = label + '\\n[JS Error] ' + err.message +
      '\\n(ดูรายละเอียดเพิ่มใน DevTools > Console และ Network tab)';
  }
}

function call(url) {
  show(fetch(url), 'GET ' + url);
}

function callWithAuth() {
  show(fetch('/api/need-auth', {
    headers: { 'Authorization': 'Bearer fake-token-12345' }
  }), 'GET /api/need-auth (with Authorization header)');
}

function callPost() {
  show(fetch('/api/echo', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: 'สวัสดี DevTools', timestamp: Date.now() })
  }), 'POST /api/echo');
}
</script>
</body>
</html>
"""


def json_response(handler, status, payload, extra_headers=None):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Content-Length", str(len(body)))
    for k, v in (extra_headers or {}).items():
        handler.send_header(k, v)
    handler.end_headers()
    handler.wfile.write(body)


class MainHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        print("[8000]", fmt % args)

    def do_GET(self):
        path = self.path.split("?")[0]

        if path == "/":
            body = HTML_PAGE.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/instant":
            json_response(self, 200, {"message": "ตอบกลับทันที", "ok": True})

        elif path == "/api/slow":
            time.sleep(2.5)
            json_response(self, 200, {"message": "รอ 2.5 วินาทีก่อนตอบ (จำลอง backend ช้า)"})

        elif path == "/api/error":
            json_response(self, 500, {"error": "Internal Server Error (จำลอง)"})

        elif path == "/api/notfound":
            json_response(self, 404, {"error": "ไม่พบ resource นี้"})

        elif path == "/api/redirect":
            self.send_response(302)
            self.send_header("Location", "/api/instant")
            self.end_headers()

        elif path == "/api/cache":
            body = json.dumps({"cached": True, "note": "ลองกดซ้ำแล้วดู Network tab"}).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "max-age=60")
            self.send_header("ETag", '"lab-etag-123"')
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        elif path == "/api/set-cookie":
            json_response(self, 200, {"message": "ส่ง cookie ไปให้แล้ว"},
                          extra_headers={"Set-Cookie": "lab_session=abc123; Path=/"})

        elif path == "/api/need-auth":
            auth = self.headers.get("Authorization")
            if not auth:
                json_response(self, 401, {"error": "ไม่มี Authorization header"})
            else:
                json_response(self, 200, {"message": "auth ผ่าน", "received_header": auth})

        elif path == "/api/large":
            payload = {"items": [{"id": i, "text": "x" * 40} for i in range(6000)]}
            json_response(self, 200, payload)

        else:
            json_response(self, 404, {"error": "unknown path"})

    def do_POST(self):
        if self.path == "/api/echo":
            length = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(length)
            try:
                data = json.loads(raw.decode("utf-8"))
            except Exception:
                data = {"raw": raw.decode("utf-8", errors="replace")}
            json_response(self, 200, {"you_sent": data, "echoed_at": time.time()})
        else:
            json_response(self, 404, {"error": "unknown path"})


class CorsDemoHandler(BaseHTTPRequestHandler):
    """เซิร์ฟเวอร์คนละ origin (port 8001) สำหรับสาธิต CORS จริงๆ"""

    def log_message(self, fmt, *args):
        print("[8001]", fmt % args)

    def do_GET(self):
        if self.path == "/allowed":
            json_response(self, 200, {"message": "origin นี้ได้รับอนุญาต"},
                          extra_headers={"Access-Control-Allow-Origin": "http://localhost:8000"})
        elif self.path == "/blocked":
            # ไม่ใส่ Access-Control-Allow-Origin เลย -> browser จะบล็อกไม่ให้ JS อ่านผล
            json_response(self, 200, {"message": "server ตอบมาปกติ แต่ browser จะบล็อกฝั่ง JS"})
        else:
            json_response(self, 404, {"error": "unknown path"})


def run_server(handler_cls, port):
    server = ThreadingHTTPServer(("localhost", port), handler_cls)
    print(f"Serving on http://localhost:{port}")
    server.serve_forever()


if __name__ == "__main__":
    t = threading.Thread(target=run_server, args=(CorsDemoHandler, 8001), daemon=True)
    t.start()
    print("=" * 60)
    print("เปิดเบราว์เซอร์ไปที่ http://localhost:8000")
    print("แล้วเปิด DevTools (F12) แท็บ Network ก่อนกดปุ่มต่างๆ ในหน้าเว็บ")
    print("=" * 60)
    run_server(MainHandler, 8000)
