from http import HTTPStatus
from flask import jsonify, make_response
from flask_restx import Namespace, Resource

from app.service import node_service
from app.api.utils.request_utils import handle_time_range_metric
from app.api.utils.api_params import DATE_PARAMS

node_ns = Namespace("node", description="Node APIs")

@node_ns.route("/list")
class NodeList(Resource):
    def get(self):
        data = node_service.node_list()
        return make_response(jsonify(data), HTTPStatus.OK)

@node_ns.route("/info/<string:node_name>")
class NodeInfo(Resource):
    def get(self, node_name):
        data = node_service.node_info(node_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@node_ns.route("/performance_summary/<string:node_name>")
class PerformanceSummary(Resource):
    def get(self, node_name):
        data = node_service.performance_summary(node_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@node_ns.route("/load_average/<string:node_name>")
@node_ns.doc(params=DATE_PARAMS)
class LoadAverage(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                node_service.load_average(node_name, start_utc, end_utc)
        )

@node_ns.route("/gpu_summary/<string:node_name>")
class GpuSummary(Resource):
    def get(self, node_name):
        data = node_service.gpu_summary(node_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@node_ns.route("/cpu_usage/<string:node_name>")
@node_ns.doc(params=DATE_PARAMS)
class NodeCPUUsage(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                node_service.cpu_usage(node_name, start_utc, end_utc)
        )

@node_ns.route("/cpu_usage_by_pod/<string:node_name>")
@node_ns.doc(params=DATE_PARAMS)
class NodeCPUUsageByPod(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                node_service.cpu_usage_by_pod(node_name, start_utc, end_utc)
        )

@node_ns.route("/memory_usage/<string:node_name>")
@node_ns.doc(params=DATE_PARAMS)
class NodeMemoryUsage(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                node_service.memory_usage(node_name, start_utc, end_utc)
        )

@node_ns.route("/memory_usage_by_pod/<string:node_name>")
@node_ns.doc(params=DATE_PARAMS)
class NodeMemoryUsageByPod(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                node_service.memory_usage_by_pod(node_name, start_utc, end_utc)
        )

@node_ns.route("/disk_io/<string:node_name>")
@node_ns.doc(params=DATE_PARAMS)
class NodeDiskIO(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                node_service.disk_io(node_name, start_utc, end_utc)
        )

@node_ns.route("/network_received/<string:node_name>")
@node_ns.doc(params=DATE_PARAMS)
class NodeNetworkReceived(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                node_service.network_received(node_name, start_utc, end_utc)
        )

@node_ns.route("/network_transmitted/<string:node_name>")
@node_ns.doc(params=DATE_PARAMS)
class NodeNetworkTransmitted(Resource):
    def get(self, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                node_service.network_transmitted(node_name, start_utc, end_utc)
        )

@node_ns.route("/disk_space_usage/<string:node_name>")
class NodeDiskSpaceUsage(Resource):
    def get(self, node_name):
        data = node_service.disk_space_usage(node_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@node_ns.route("/running_pods/<string:node_name>")
class NodeRunningPods(Resource):
    def get(self, node_name):
        data = node_service.running_pods(node_name)
        return make_response(jsonify(data), HTTPStatus.OK)
