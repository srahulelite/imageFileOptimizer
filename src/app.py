from flask import Flask, send_from_directory, jsonify
import os
from observability.request_context import start_request, end_request

def create_app():
    # static_folder set relative to src file location -> "../frontend" points to project_root/frontend
    app = Flask(__name__, static_folder=os.path.join(os.path.dirname(__file__), "..", "frontend"), static_url_path="/")

    # register blueprints if available
    try:
        from routes.health import health_bp
        app.register_blueprint(health_bp, url_prefix="/api")
    except Exception:
        pass

    try:
        from routes.video_upload import video_bp
        app.register_blueprint(video_bp, url_prefix="/api")
    except Exception:
        pass

    try:
        from routes.image_upload import upload_bp
        app.register_blueprint(upload_bp, url_prefix="/api")
    except Exception:
        pass

    try:
        from routes.metrics import metrics_bp
        app.register_blueprint(metrics_bp, url_prefix="/api")
    except Exception:
        pass

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")
    
    @app.before_request
    def _before():
        start_request()

    @app.after_request
    def _after(response):
        return end_request(response)
    
    

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
    # create_app().run(debug=True, port=5000)
