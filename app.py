from __future__ import annotations
from flask import Flask, jsonify
from config import Config, ensure_dirs
from services.model import RandomForestPredictor
from api.predict import bp_predict
from api.satellite import bp_sat

def create_app() -> Flask:
    cfg = Config()
    ensure_dirs(cfg)

    app = Flask(__name__)
    app.config.from_mapping(
        MODEL_PATH=cfg.MODEL_PATH,
        MODEL_VERSION=cfg.MODEL_VERSION,
        IMAGE_DIR=cfg.IMAGE_DIR,
        MAX_CONTENT_LENGTH=cfg.MAX_CONTENT_LENGTH,
    )

    # Load predictor (lazy-load model file on first use)
    app.extensions["rf_predictor"] = RandomForestPredictor(
        model_path=app.config["MODEL_PATH"],
        model_version=app.config["MODEL_VERSION"],
    )

    app.register_blueprint(bp_predict)
    app.register_blueprint(bp_sat)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"}), 200

    return app

if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=True)
