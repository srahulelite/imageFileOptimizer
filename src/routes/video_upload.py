from flask import Blueprint, request, jsonify, send_file, after_this_request
import tempfile
import os
import zipfile
import shutil
import datetime
import traceback
from flask import g
from observability.metrics import inc

from services.compression.video_compress import compress_video

video_bp = Blueprint("video", __name__)

MAX_VIDEOS = 2
MAX_FILE_SIZE = 150 * 1024 * 1024
MAX_TOTAL_SIZE = 300 * 1024 * 1024
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm"}

def log_debug(msg, request_id=None):
    try:
        os.makedirs("storage", exist_ok=True)
        rid = request_id or getattr(g, "request_id", "unknown")
        with open(os.path.join("storage", "error_debug.log"), "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.datetime.utcnow().isoformat()} [{rid}] {msg}\n")
    except Exception:
        pass

@video_bp.route("/video/optimize", methods=["POST"])
def optimize_videos():
    files = request.files.getlist("files[]")

    inc("video_batches")
    log_debug(
        f"Video batch received: {len(files)} files",
        request_id=g.request_id
    )

    if not files:
        return jsonify({"message": "No video files uploaded"}), 400

    if len(files) > MAX_VIDEOS:
        inc("video_failures")
        log_debug("Rejected: too many videos", g.request_id)
        return jsonify({"message": "Maximum 2 videos allowed"}), 400

    total_size = 0
    for f in files:
        if not f.filename:
            return jsonify({"message": "Invalid file"}), 400

        ext = os.path.splitext(f.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            inc("video_failures")
            log_debug(f"Rejected unsupported type: {f.filename}", g.request_id)
            return jsonify({"message": f"Unsupported video type: {ext}"}), 400

        size = f.content_length
        if size is None or size > MAX_FILE_SIZE:
            return jsonify({"message": f"{f.filename} exceeds 150 MB"}), 400

        total_size += size

    if total_size > MAX_TOTAL_SIZE:
        return jsonify({"message": "Total video size exceeds 300 MB"}), 400

    quality = request.form.get("quality", "avg")

    workdir = tempfile.mkdtemp(prefix="video_")
    output_files = []

    try:
        for f in files:
            input_path = os.path.join(workdir, f.filename)
            f.save(input_path)

            output_path = compress_video(
                input_path=input_path,
                output_dir=workdir,
                quality=quality
            )
            output_files.append(output_path)

        zip_path = os.path.join(workdir, "optimized_videos.zip")
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for p in output_files:
                zf.write(p, arcname=os.path.basename(p))

        @after_this_request
        def cleanup(response):
            shutil.rmtree(workdir, ignore_errors=True)
            return response

        log_debug(
            f"Video batch processed successfully: {len(output_files)} outputs",
            request_id=g.request_id
        )
        return send_file(
            zip_path,
            as_attachment=True,
            download_name="optimized_videos.zip"
        )

    except Exception as e:
        inc("video_failures")
        tb = traceback.format_exc()
        log_debug(
            f"Video processing failed: {str(e)}\n{tb}",
            request_id=g.request_id
        )
        shutil.rmtree(workdir, ignore_errors=True)
        return jsonify({"message": "Video processing failed", "error": str(e)}), 500
