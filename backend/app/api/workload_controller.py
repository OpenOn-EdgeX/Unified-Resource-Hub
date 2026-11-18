from http import HTTPStatus
from flask import jsonify, make_response
from flask_restx import Namespace, Resource
from app.api.utils.api_params import DATE_PARAMS
from app.api.utils.request_utils import handle_time_range_metric
from app.service import workload_service

workload_ns = Namespace("workload", description="Workload APIs")

@workload_ns.route("/namespace_list")
class NamespaceList(Resource):
    def get(self):
        data = workload_service.namespace_list()
        return make_response(jsonify(data), HTTPStatus.OK)

@workload_ns.route("/workload_status/<string:namespace_name>")
class WorkloadStatus(Resource):
    def get(self, namespace_name):
        data = workload_service.workload_status(namespace_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@workload_ns.route("/workload_list/<string:namespace_name>")
class WorkloadList(Resource):
    def get(self, namespace_name):
        data = workload_service.workload_list(namespace_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@workload_ns.route("/cpu_usage/<string:namespace_name>/<string:workload_type>/<string:workload_name>")
@workload_ns.doc(params=DATE_PARAMS)
class WorkloadCPUUsage(Resource):
    def get(self, namespace_name, workload_type, workload_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                workload_service.cpu_usage(namespace_name, workload_type, workload_name, start_utc, end_utc)
        )

@workload_ns.route("/memory_usage/<string:namespace_name>/<string:workload_type>/<string:workload_name>")
@workload_ns.doc(params=DATE_PARAMS)
class WorkloadMemoryUsage(Resource):
    def get(self, namespace_name, workload_type, workload_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                workload_service.memory_usage(namespace_name, workload_type, workload_name, start_utc, end_utc)
        )

@workload_ns.route("/network_received/<string:namespace_name>/<string:workload_type>/<string:workload_name>")
@workload_ns.doc(params=DATE_PARAMS)
class WorkloadNetworkReceived(Resource):
    def get(self, namespace_name, workload_type, workload_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                workload_service.network_received(namespace_name, workload_type, workload_name, start_utc, end_utc)
        )

@workload_ns.route("/network_transmitted/<string:namespace_name>/<string:workload_type>/<string:workload_name>")
@workload_ns.doc(params=DATE_PARAMS)
class WorkloadNetworkTransmitted(Resource):
    def get(self, namespace_name, workload_type, workload_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc:
                workload_service.network_transmitted(namespace_name, workload_type, workload_name, start_utc, end_utc)
        )

@workload_ns.route("/pod_list/<string:namespace_name>/<string:workload_name>")
class WorkloadPodList(Resource):
    def get(self, namespace_name, workload_name):
        data = workload_service.pod_list(namespace_name, workload_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@workload_ns.route("/events/<string:namespace_name>/<string:workload_name>")
class WorkloadEvents(Resource):
    def get(self, namespace_name, workload_name):
        data = workload_service.events(namespace_name, workload_name)
        return make_response(jsonify(data), HTTPStatus.OK)
