import time

METRICS = {
    "image_batches": 0,
    "image_files_total": 0,
    "image_failures": 0,
    "video_batches": 0,
    "video_failures": 0,
}

def inc(key, value=1):
    METRICS[key] = METRICS.get(key, 0) + value

def snapshot():
    return dict(METRICS)
