from flask import Flask, send_from_directory, jsonify
import os

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
        from routes.upload import upload_bp
        app.register_blueprint(upload_bp, url_prefix="/api")
    except Exception:
        pass

    @app.route("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    return app

if __name__ == "__main__":
    create_app().run(debug=True, port=5000)




