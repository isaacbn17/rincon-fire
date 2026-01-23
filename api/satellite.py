from __future__ import annotations
from flask import Blueprint, request, jsonify, current_app, send_from_directory
from services.satellite_images import (
    SatelliteRequest,
    build_filename,
    get_satellite_image_bytes,
    save_image_bytes,
)

bp_sat = Blueprint("satellite", __name__)

@bp_sat.post("/api/v1/satellite/image")
def satellite_image():
    payload = request.get_json(silent=True) or {}

    try:
        lat = float(payload["lat"])
        lon = float(payload["lon"])
    except Exception:
        return jsonify({"error": "lat and lon are required and must be numbers"}), 400

    try:
        zoom = int(payload.get("zoom", 8))
    except (TypeError, ValueError):
        return jsonify({"error": "zoom must be an integer"}), 400

    fmt = str(payload.get("format", "png")).lower()
    if fmt not in {"png", "jpg", "jpeg"}:
        return jsonify({"error": "format must be one of: png, jpg, jpeg"}), 400

    return_image = bool(payload.get("return_image", False))

    req_obj = SatelliteRequest(lat=lat, lon=lon, zoom=zoom, fmt=("jpg" if fmt == "jpeg" else fmt))

    try:
        img_bytes = get_satellite_image_bytes(req_obj)
    except Exception as exc:
        return jsonify({"error": str(exc)}), 502

    filename = build_filename(req_obj)
    out_path = save_image_bytes(current_app.config["IMAGE_DIR"], filename, img_bytes)

    if return_image:
        return send_from_directory(
            directory=current_app.config["IMAGE_DIR"],
            path=filename,
            as_attachment=False,
        )

    return jsonify({
        "lat": lat,
        "lon": lon,
        "zoom": zoom,
        "format": req_obj.fmt,
        "filename": filename,
        "path": str(out_path.as_posix())
    }), 200

@bp_sat.get("/api/v1/satellite/image/<path:filename>")
def get_saved_satellite(filename: str):
    # Basic guardrails: only serve from IMAGE_DIR
    return send_from_directory(
        directory=current_app.config["IMAGE_DIR"],
        path=filename,
        as_attachment=False,
    )
