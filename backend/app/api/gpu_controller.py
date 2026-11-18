from http import HTTPStatus
from flask import jsonify, make_response
from flask_restx import Namespace, Resource
from app.api.utils.api_params import DATE_PARAMS
from app.api.utils.request_utils import handle_time_range_metric

from app.service import gpu_service

gpu_ns = Namespace("gpu", description="GPU APIs")

@gpu_ns.route("/node_list")
class NodeList(Resource):
    def get(self):
        data = gpu_service.node_list()
        return make_response(jsonify(data), HTTPStatus.OK)

@gpu_ns.route("/status/<string:node_name>")
class GPUStatus(Resource):
    def get(self, node_name):
        data = gpu_service.gpu_status(node_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@gpu_ns.route("/core/gpu_utilization/<string:node_name>")
@gpu_ns.doc(params=DATE_PARAMS)
class GPUUtilization(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: gpu_service.gpu_utilization(
                node_name, start_utc, end_utc
            )
        )

@gpu_ns.route("/core/sm_clock/<string:node_name>")
@gpu_ns.doc(params=DATE_PARAMS)
class SMClock(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: gpu_service.sm_clock(
                node_name, start_utc, end_utc
            )
        )

@gpu_ns.route("/core/p_state/<string:node_name>")
@gpu_ns.doc(params=DATE_PARAMS)
class PState(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: gpu_service.p_state(
                node_name, start_utc, end_utc
            )
        )

@gpu_ns.route("/core/encoder_utilization/<string:node_name>")
@gpu_ns.doc(params=DATE_PARAMS)
class EncoderUtilization(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: gpu_service.encoder_utilization(
                node_name, start_utc, end_utc
            )
        )

@gpu_ns.route("/core/decoder_utilization/<string:node_name>")
@gpu_ns.doc(params=DATE_PARAMS)
class DecoderUtilization(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: gpu_service.decoder_utilization(
                node_name, start_utc, end_utc
            )
        )

@gpu_ns.route("/memory/memory_utilization/<string:node_name>")
@gpu_ns.doc(params=DATE_PARAMS)
class MemoryUtilization(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: gpu_service.memory_utilization(
                node_name, start_utc, end_utc
            )
        )

@gpu_ns.route("/memory/vram_usage/<string:node_name>")
@gpu_ns.doc(params=DATE_PARAMS)
class VRAMUsage(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: gpu_service.vram_usage(
                node_name, start_utc, end_utc
            )
        )

@gpu_ns.route("/memory/memory_clock/<string:node_name>")
@gpu_ns.doc(params=DATE_PARAMS)
class MemoryClock(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: gpu_service.memory_clock(
                node_name, start_utc, end_utc
            )
        )

@gpu_ns.route("/thermal/gpu_temperature/<string:node_name>")
@gpu_ns.doc(params=DATE_PARAMS)
class GPUTemperature(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: gpu_service.gpu_temperature(
                node_name, start_utc, end_utc
            )
        )

@gpu_ns.route("/thermal/memory_temperature/<string:node_name>")
@gpu_ns.doc(params=DATE_PARAMS)
class MemoryTemperature(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: gpu_service.memory_temperature(
                node_name, start_utc, end_utc
            )
        )

@gpu_ns.route("/power_usage/<string:node_name>")
@gpu_ns.doc(params=DATE_PARAMS)
class PowerUsage(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: gpu_service.power_usage(
                node_name, start_utc, end_utc
            )
        )

@gpu_ns.route("/health_errors/<string:node_name>")
@gpu_ns.doc(params=DATE_PARAMS)
class HealthErrors(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: gpu_service.health_errors(
                node_name, start_utc, end_utc
            )
        )

@gpu_ns.route("/info/<string:node_name>")
class GPUInfo(Resource):
    def get(self, node_name):
        data = gpu_service.gpu_info(node_name)
        return make_response(jsonify(data), HTTPStatus.OK)
