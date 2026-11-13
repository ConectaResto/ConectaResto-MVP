from flask import jsonify


def register_error_handlers(app):
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({"success": False, "error": "Solicitud inválida"}), 400

    @app.errorhandler(401)
    def unauthorized(error):
        return jsonify({"success": False, "error": "No autorizado"}), 401

    @app.errorhandler(403)
    def forbidden(error):
        return jsonify({"success": False, "error": "Prohibido"}), 403

    @app.errorhandler(404)
    def not_found(error):
        return jsonify({"success": False, "error": "No encontrado"}), 404

    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({"success": False, "error": "Error interno del servidor"}), 500