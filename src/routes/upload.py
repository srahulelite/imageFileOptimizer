from flask import Blueprint, request, jsonify

upload_bp = Blueprint("upload", __name__)

@upload_bp.route("/upload", methods=["POST"])
def upload_stub():
    """
    Upload endpoint stub.
    Currently returns 501 Not Implemented so frontend can be wired safely.
    We'll replace this with real logic later (Milestone 1).
    """
    # We accept the request but do not process yet.
    return jsonify({"message":"Not implemented yet", "hint":"This is a stub. Implement upload logic in Milestone 1."}), 501
