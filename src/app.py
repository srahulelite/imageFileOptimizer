from flask import Flask, send_from_directory, jsonify

def create_app():
    app = Flask(__name__, static_folder="frontend", static_url_path="/")

    # try to register blueprints if modules exist
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
        # serve frontend/index.html
        return send_from_directory(app.static_folder, "index.html")

    return app

if __name__ == "__main__":
    create_app().run(debug=True, port=5000)
