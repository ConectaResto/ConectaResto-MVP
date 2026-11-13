from flask import jsonify


def success_response(data=None, message=None, status_code=200):
    response = {"success": True}
    if data is not None:
        response["data"] = data
    if message is not None:
        response["message"] = message
    return jsonify(response), status_code


def error_response(message, status_code=400, errors=None):
    response = {"success": False, "error": message}
    if errors is not None:
        response["errors"] = errors
    return jsonify(response), status_code