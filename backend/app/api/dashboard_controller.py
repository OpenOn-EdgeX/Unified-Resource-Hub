from http import HTTPStatus
from flask import jsonify, make_response
from flask_restx import Namespace, Resource

from app.service import dashboard_service

dashboard_ns = Namespace("dashboard", description="Dashboard APIs")

@dashboard_ns.route("/nodes")
class Nodes(Resource):
    def get(self):
        data = dashboard_service.nodes()
        return make_response(jsonify(data), HTTPStatus.OK)

@dashboard_ns.route("/namespaces")
class Namespaces(Resource):
    def get(self):
        data = dashboard_service.namespaces()
        return make_response(jsonify(data), HTTPStatus.OK)

@dashboard_ns.route("/pods")
class Pods(Resource):
    def get(self):
        data = dashboard_service.pods()
        return make_response(jsonify(data), HTTPStatus.OK)

@dashboard_ns.route("/workloads")
class WorkLoads(Resource):
    def get(self):
        data = dashboard_service.workloads()
        return make_response(jsonify(data), HTTPStatus.OK)

@dashboard_ns.route("/services")
class Services(Resource):
    def get(self):
        data = dashboard_service.services()
        return make_response(jsonify(data), HTTPStatus.OK)

@dashboard_ns.route("/resource_usage")
class ResourceUsage(Resource):
    def get(self):
        data = dashboard_service.resource_usage()
        return make_response(jsonify(data), HTTPStatus.OK)

@dashboard_ns.route("/gpu_usage")
class GpuUsage(Resource):
    def get(self):
        data = dashboard_service.gpu_usage()
        return make_response(jsonify(data), HTTPStatus.OK)

@dashboard_ns.route("/disk_io")
class DiskIO(Resource):
    def get(self):
        data = dashboard_service.disk_io()
        return make_response(jsonify(data), HTTPStatus.OK)

@dashboard_ns.route("/network_io")
class NetworkIO(Resource):
    def get(self):
        data = dashboard_service.network_io()
        return make_response(jsonify(data), HTTPStatus.OK)

@dashboard_ns.route("/cpu_top_5")
class CpuTop(Resource):
    def get(self):
        data = dashboard_service.cpu_top_5()
        return make_response(jsonify(data), HTTPStatus.OK)

@dashboard_ns.route("/memory_top_5")
class MemoryTop(Resource):
    def get(self):
        data = dashboard_service.memory_top_5()
        return make_response(jsonify(data), HTTPStatus.OK)

@dashboard_ns.route("/events")
class Events(Resource):
    def get(self):
        data = dashboard_service.events()
        return make_response(jsonify(data), HTTPStatus.OK)
