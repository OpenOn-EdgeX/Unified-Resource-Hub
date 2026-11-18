from http import HTTPStatus
from flask import request, jsonify, make_response
from utils.time_utils import parse_kst_to_utc

def handle_time_range_metric(service_func, required_params=None):
    required_params = required_params or []

    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        return make_response(
            jsonify({"message": "start_date and end_date are required"}),
            HTTPStatus.BAD_REQUEST
        )

    try:
        start_utc = parse_kst_to_utc(start_date)
        end_utc = parse_kst_to_utc(end_date)
    except ValueError:
        return make_response(
            jsonify({"message": "Invalid datetime format. Use ISO8601 (KST)"}),
            HTTPStatus.BAD_REQUEST
        )

    extra_args = {}
    for param in required_params:
        value = request.args.get(param)
        if not value:
            return make_response(
                jsonify({"message": f"{param} is required"}),
                HTTPStatus.BAD_REQUEST
            )
        extra_args[param] = value

    data = service_func(start_utc, end_utc, **extra_args)
    return make_response(jsonify(data), HTTPStatus.OK)
