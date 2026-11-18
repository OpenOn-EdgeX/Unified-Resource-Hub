from http import HTTPStatus
from flask import jsonify, make_response
from flask_restx import Namespace, Resource
from app.service import storage_service

storage_ns = Namespace("storage", description="Storage APIs")

@storage_ns.route("/namespace_list")
class NamespaceList(Resource):
    def get(self):
        data = storage_service.namespace_list()
        return make_response(jsonify(data), HTTPStatus.OK)

@storage_ns.route("/pvc_status/<string:namespace_name>")
class PVCSummary(Resource):
    def get(self, namespace_name):
        data = storage_service.pvc_status(namespace_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@storage_ns.route("/pvc_list/<string:namespace_name>")
class PVCList(Resource):
    def get(self, namespace_name):
        data = storage_service.pvc_list(namespace_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@storage_ns.route("/pvc_capacity/<string:namespace_name>/<string:pvc_name>")
class PVCCapacity(Resource):
    def get(self, namespace_name, pvc_name):
        pass

@storage_ns.route("/pvc_bound_volume/<string:namespace_name>/<string:pvc_name>")
class PVCBoundVolume(Resource):
    def get(self, namespace_name, pvc_name):
        data = storage_service.pvc_bound_volume(namespace_name, pvc_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@storage_ns.route("/pvc_connected_pods/<string:namespace_name>/<string:pvc_name>")
class PVCConnectedPods(Resource):
    def get(self, namespace_name, pvc_name):
        data = storage_service.pvc_connected_pods(namespace_name, pvc_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@storage_ns.route("/pvc_events/<string:namespace_name>/<string:pvc_name>")
class PVCEvents(Resource):
    def get(self, namespace_name, pvc_name):
        data = storage_service.pvc_events(namespace_name, pvc_name)
        return make_response(jsonify(data), HTTPStatus.OK)

@storage_ns.route("/pv_sc_status")
class PVSCSummary(Resource):
    def get(self):
        data = storage_service.pv_sc_status()
        return make_response(jsonify(data), HTTPStatus.OK)

@storage_ns.route("/pv_list")
class PVList(Resource):
    def get(self):
        data = storage_service.pv_list()
        return make_response(jsonify(data), HTTPStatus.OK)

@storage_ns.route("/sc_list")
class SCList(Resource):
    def get(self):
        data = storage_service.sc_list()
        return make_response(jsonify(data), HTTPStatus.OK)
