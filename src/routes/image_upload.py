from flask import Blueprint, request, jsonify, send_file, after_this_request
import tempfile
import os
import uuid
import shutil
import traceback
import datetime
from services.compression.image_compress import compress_image_to_path
from observability.metrics import inc

upload_bp = Blueprint("upload", __name__)

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}

MAX_IMAGES = 5
MAX_FILE_SIZE = 30 * 1024 * 1024      # 30 MB
MAX_TOTAL_SIZE = 150 * 1024 * 1024    # 150 MB

def allowed_filename(filename):
    _, ext = os.path.splitext(filename.lower())
    return ext in ALLOWED_EXT

def log_debug(msg, request_id=None):
    try:
        os.makedirs("storage", exist_ok=True)
        rid = request_id or getattr(request, "request_id", "unknown")
        with open(os.path.join("storage", "error_debug.log"), "a", encoding="utf-8") as fh:
            fh.write(f"{datetime.datetime.utcnow().isoformat()} [{rid}] {msg}\n")
    except Exception:
        pass


@upload_bp.route("/upload", methods=["POST"])
def upload_and_compress():
    files = request.files.getlist("files[]")
    log_debug(f"Received upload request: {len(files)} files", request_id=getattr(request, "request_id", None))
    inc("image_batches")
    inc("image_files_total", len(files))
    if not files:
        return jsonify({"message":"No files uploaded"}), 400
    
    # ---- HARD VALIDATION (count & size) ----
    if len(files) > MAX_IMAGES:
        inc("image_failures")
        return jsonify({
            "message": f"Maximum {MAX_IMAGES} images allowed per upload"
        }), 400

    total_size = 0
    for f in files:
        size = f.content_length
        if size is None:
            return jsonify({"message": "Unable to determine file size"}), 400

        if size > MAX_FILE_SIZE:
            inc("image_failures")
            return jsonify({
                "message": f"{f.filename} exceeds 30 MB limit"
            }), 400

        total_size += size

    if total_size > MAX_TOTAL_SIZE:
        inc("image_failures")
        return jsonify({
            "message": "Total image size exceeds 150 MB limit"
        }), 400
    # ---- END HARD VALIDATION ----

    quality = request.form.get("quality", "avg")
    if quality not in ("low", "avg", "high"):
        quality = "avg"

    workdir = tempfile.mkdtemp(prefix="ifo_")
    try:
        out_files = []
        for f in files:
            original_name = f.filename or f"upload_{uuid.uuid4().hex}"
            if not allowed_filename(original_name):
                # skip unsupported file types (still allow others)
                log_debug(f"Skipping unsupported file: {original_name}")
                continue

            in_path = os.path.join(workdir, "input_" + uuid.uuid4().hex + "_" + original_name)
            try:
                f.save(in_path)
            except Exception as e:
                log_debug(f"Save failed for {original_name}: {e}")
                raise

            base, ext = os.path.splitext(original_name)
            # caller's expected out_path (may not actually be written if compressor changes extension)
            expected_out_filename = f"optimized_{base}{ext}"
            expected_out_path = os.path.join(workdir, expected_out_filename)

            # run compressor (may create a file with different extension/name)
            try:
                compress_image_to_path(in_path, expected_out_path, quality)
            except Exception as e:
                # log and continue with next files; don't crash entire batch
                log_debug(f"Compression failed for {original_name}: {e}\\n{traceback.format_exc()}")
                continue

            # If expected_out_path wasn't created (compressor may have written different filename),
            # try to find the actual file created in workdir that starts with "optimized_<base>"
            actual_out_path = expected_out_path
            actual_out_filename = expected_out_filename
            if not os.path.exists(actual_out_path):
                # search for any matching files
                prefix = f"optimized_{base}"
                matches = [p for p in os.listdir(workdir) if p.startswith(prefix)]
                if matches:
                    # prefer first match (there will typically be one)
                    candidate = matches[0]
                    actual_out_path = os.path.join(workdir, candidate)
                    actual_out_filename = candidate
                    log_debug(f"Expected output {expected_out_filename} not found; using {candidate}")
                else:
                    # nothing to add for this file; skip it
                    log_debug(f"No output found for {original_name}; skipping.")
                    continue

            out_files.append((actual_out_path, actual_out_filename))

        if not out_files:
            shutil.rmtree(workdir)
            return jsonify({"message":"No supported/processed image files in upload"}), 400

        # create zip
        zip_path = os.path.join(workdir, f"batch_{uuid.uuid4().hex}.zip")
        import zipfile
        with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for p, arcname in out_files:
                # guard: only write files that actually exist
                if os.path.exists(p):
                    zf.write(p, arcname=arcname)
                else:
                    log_debug(f"File disappeared before zipping: {p}")

        @after_this_request
        def cleanup(response):
            try:
                if os.path.exists(workdir):
                    shutil.rmtree(workdir)
            except Exception:
                pass
            return response
        log_debug(f"Image batch processed successfully: {len(out_files)} outputs", request_id=getattr(request, "request_id", None))
        return send_file(zip_path, as_attachment=True, download_name="optimized_batch.zip", mimetype="application/zip")

    except Exception as e:
        tb = traceback.format_exc()
        log_debug(f"Processing failed: {str(e)}\\n{tb}")
        return jsonify({"message":"Processing failed", "error": str(e), "traceback": tb}), 500
