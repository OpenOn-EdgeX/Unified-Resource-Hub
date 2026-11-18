from http import HTTPStatus
from flask import jsonify, make_response
from flask_restx import Namespace, Resource
from app.api.utils.api_params import DATE_PARAMS
from app.api.utils.request_utils import handle_time_range_metric
from app.service import service_service

service_ns = Namespace("service", description="Service APIs")

@service_ns.route("/namespace_list")
class NamespaceList(Resource):
    def get(self):
        data = service_service.namespace_list()
        return make_response(jsonify(data), HTTPStatus.OK)

@service_ns.route("/service_type_list")
class ServiceTypeList(Resource):
    def get(self):
        data = service_service.service_type_list()
        return make_response(jsonify(data), HTTPStatus.OK)

@service_ns.route("/service_status/<string:namespace_name>/<string:service_type>")
class ServiceStatus(Resource):
    def get(self, namespace_name, service_type):
        data = service_service.service_status(namespace_name, service_type)
        return make_response(jsonify(data), HTTPStatus.OK)

@service_ns.route("/service_list/<string:namespace_name>/<string:service_type>")
class ServiceList(Resource):
    def get(self, namespace_name, service_type):
        data = service_service.service_list(namespace_name, service_type)
        return make_response(jsonify(data), HTTPStatus.OK)

@service_ns.route("/network_received/<string:namespace_name>/<string:service_name>")
@service_ns.doc(params=DATE_PARAMS)
class ServiceNetworkReceived(Resource):
    def get(self, namespace_name, service_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: service_service.network_received(
                namespace_name, service_name, start_utc, end_utc
            )
        )

@service_ns.route("/network_transmitted/<string:namespace_name>/<string:service_name>")
@service_ns.doc(params=DATE_PARAMS)
class ServiceNetworkTransmitted(Resource):
    def get(self, namespace_name, service_name):
        return handle_time_range_metric(
            lambda start_utc, end_utc: service_service.network_transmitted(
                namespace_name, service_name, start_utc, end_utc
            )
        )

@service_ns.route("/endpoint_list/<string:namespace_name>/<string:service_name>")
class ServiceEndpointList(Resource):
    def get(self, namespace_name, service_name):
        data = service_service.endpoint_list(namespace_name, service_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@service_ns.route("/events/<string:namespace_name>/<string:service_name>")
class ServiceEvents(Resource):
    def get(self, namespace_name, service_name):
        data = service_service.events(namespace_name, service_name)
        return make_response(jsonify(data), HTTPStatus.OK)
