import uuid
import time
from flask import g, request

def start_request():
    g.request_id = uuid.uuid4().hex[:12]
    g.start_time = time.time()

def end_request(response):
    duration_ms = int((time.time() - g.start_time) * 1000)

    log = {
        "request_id": g.request_id,
        "method": request.method,
        "path": request.path,
        "status": response.status_code,
        "duration_ms": duration_ms,
        "content_length": request.content_length
    }

    print(f"[REQUEST] {log}")
    return response
