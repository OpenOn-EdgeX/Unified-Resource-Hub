from http import HTTPStatus
from flask import jsonify, make_response
from flask_restx import Namespace, Resource

from app.service import cluster_service
from app.api.utils.request_utils import handle_time_range_metric
from app.api.utils.api_params import DATE_PARAMS

cluster_ns = Namespace("cluster", description="Cluster APIs")

@cluster_ns.route("/status")
class ClusterStatus(Resource):
    def get(self):
        data = cluster_service.cluster_status()
        return make_response(jsonify(data), HTTPStatus.OK)

@cluster_ns.route("/utilization")
class Utilization(Resource):
    def get(self):
        data = cluster_service.utilization()
        return make_response(jsonify(data), HTTPStatus.OK)

@cluster_ns.route("/cpu_usage_by_namespace")
@cluster_ns.doc(params=DATE_PARAMS)
class ClusterCPUUsageByNamespace(Resource):
    def get(self):
        return handle_time_range_metric(
            cluster_service.cpu_usage_by_namespace
        )

@cluster_ns.route("/memory_usage_by_namespace")
@cluster_ns.doc(params=DATE_PARAMS)
class ClusterMemoryUsageByNamespace(Resource):
    def get(self):
        return handle_time_range_metric(
            cluster_service.memory_usage_by_namespace
        )

@cluster_ns.route("/network_rx_by_namespace")
@cluster_ns.doc(params=DATE_PARAMS)
class ClusterNetworkRXByNamespace(Resource):
    def get(self):
        return handle_time_range_metric(
            cluster_service.network_rx_by_namespace
        )

@cluster_ns.route("/network_tx_by_namespace")
@cluster_ns.doc(params=DATE_PARAMS)
class ClusterNetworkTXByNamespace(Resource):
    def get(self):
        return handle_time_range_metric(
            cluster_service.network_tx_by_namespace
        )

@cluster_ns.route("/disk_iops_by_namespace")
@cluster_ns.doc(params=DATE_PARAMS)
class ClusterDiskIOPSByNamespace(Resource):
    def get(self):
        return handle_time_range_metric(
            cluster_service.disk_iops_by_namespace
        )

@cluster_ns.route("/disk_throughput_by_namespace")
@cluster_ns.doc(params=DATE_PARAMS)
class ClusterDiskThroughputByNamespace(Resource):
    def get(self):
        return handle_time_range_metric(
            cluster_service.disk_throughput_by_namespace
        )

@cluster_ns.route("/summary_by_namespace")
class SummaryByNamespace(Resource):
    def get(self):
        data = cluster_service.summary_by_namespace()
        return make_response(jsonify(data), HTTPStatus.OK)

@cluster_ns.route("/cluster_events")
class ClusterEvents(Resource):
    def get(self):
        data = cluster_service.cluster_events()
        return make_response(jsonify(data), HTTPStatus.OK)
