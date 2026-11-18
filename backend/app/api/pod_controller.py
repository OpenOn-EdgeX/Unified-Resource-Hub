from http import HTTPStatus
from flask import jsonify, make_response
from flask_restx import Namespace, Resource
from app.api.utils.api_params import DATE_PARAMS
from app.api.utils.request_utils import handle_time_range_metric
from app.service import pod_service

pod_ns = Namespace("pod", description="Pod APIs")

@pod_ns.route("/namespace_list")
class NamespaceList(Resource):
    def get(self):
        data = pod_service.namespace_list()
        return make_response(jsonify(data), HTTPStatus.OK)

@pod_ns.route("/node_list")
class NodeList(Resource):
    def get(self):
        data = pod_service.node_list()
        return make_response(jsonify(data), HTTPStatus.OK)

@pod_ns.route("/pod_status/<string:namespace_name>/<string:node_name>")
class PodStatus(Resource):
    def get(self, namespace_name, node_name):
        data = pod_service.pod_status(namespace_name, node_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@pod_ns.route("/cpu_usage/<string:namespace_name>/<string:node_name>")
@pod_ns.doc(params=DATE_PARAMS)
class PodCPUUsage(Resource):
    def get(self, namespace_name, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                pod_service.cpu_usage(namespace_name, node_name, start_utc, end_utc)
        )

@pod_ns.route("/memory_usage/<string:namespace_name>/<string:node_name>")
@pod_ns.doc(params=DATE_PARAMS)
class PodMemoryUsage(Resource):
    def get(self, namespace_name, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                pod_service.memory_usage(namespace_name, node_name, start_utc, end_utc)
        )

@pod_ns.route("/network_received/<string:namespace_name>/<string:node_name>")
@pod_ns.doc(params=DATE_PARAMS)
class PodNetworkReceived(Resource):
    def get(self, namespace_name, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                pod_service.network_received(namespace_name, node_name, start_utc, end_utc)
        )

@pod_ns.route("/network_transmitted/<string:namespace_name>/<string:node_name>")
@pod_ns.doc(params=DATE_PARAMS)
class PodNetworkTransmitted(Resource):
    def get(self, namespace_name, node_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                pod_service.network_transmitted(namespace_name, node_name, start_utc, end_utc)
        )

@pod_ns.route("/pod_list/<string:namespace_name>/<string:node_name>")
class PodList(Resource):
    def get(self, namespace_name, node_name):
        data = pod_service.pod_list(namespace_name, node_name)
        return make_response(jsonify(data), HTTPStatus.OK)
