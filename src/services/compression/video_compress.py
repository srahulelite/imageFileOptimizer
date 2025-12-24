import os
import subprocess
import uuid

QUALITY_PRESETS = {
    "low":  {"crf": "32", "preset": "veryfast"},
    "avg":  {"crf": "26", "preset": "medium"},
    "high": {"crf": "20", "preset": "slow"},
}

ALLOWED_EXTENSIONS = {".mp4", ".mov", ".webm"}

def compress_video(input_path: str, output_dir: str, quality: str) -> str:
    """
    Compress a video using FFmpeg.
    Returns output file path.
    """
    ext = os.path.splitext(input_path)[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise ValueError("Unsupported video format")

    preset_cfg = QUALITY_PRESETS.get(quality, QUALITY_PRESETS["avg"])

    output_name = f"optimized_{uuid.uuid4().hex}.mp4"
    output_path = os.path.join(output_dir, output_name)

    cmd = [
        "ffmpeg",
        "-y",
        "-i", input_path,
        "-vcodec", "libx264",
        "-crf", preset_cfg["crf"],
        "-preset", preset_cfg["preset"],
        "-movflags", "+faststart",
        "-acodec", "aac",
        "-b:a", "128k",
        output_path
    ]

    subprocess.run(
        cmd,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=True
    )

    return output_path
