from flask import Blueprint, jsonify
from observability.metrics import snapshot

metrics_bp = Blueprint("metrics", __name__)

@metrics_bp.route("/metrics", methods=["GET"])
def metrics():
    return jsonify(snapshot())
