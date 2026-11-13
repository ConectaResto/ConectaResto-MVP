from flask import Blueprint, jsonify
from app.health.service import get_health_status

health_bp = Blueprint("health", __name__)


@health_bp.get("/health")
def health():
    return jsonify(get_health_status()), 200