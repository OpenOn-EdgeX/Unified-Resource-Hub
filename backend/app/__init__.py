import os
import re
from pathlib import Path

from flask import Blueprint, Flask, request, send_from_directory
from flask_restx import Api

from app.api import namespaces
from app.exceptions import ApiException


def create_app():
    app = Flask(__name__, static_folder=None)
    app.config.from_mapping(
        KUBECONFIG=os.environ.get('KUBECONFIG'),
        PROMETHEUS_URL=os.environ.get('PROMETHEUS_URL'),
        CLUSTER_NAME=os.environ.get('CLUSTER_NAME'),
        RESTX_MASK_SWAGGER=False,
    )
    routes = Blueprint('monitoring', __name__)
    api = Api(routes, title='Unified Resource Hub', version='1.0', doc=False)
    for namespace, route in namespaces:
        api.add_namespace(namespace, path=route)

    @api.errorhandler(ApiException)
    def handle_service_error(error):
        return {'code': error.code, 'message': error.message}, error.status_code

    @routes.before_request
    def check_resource_names():
        for name in (request.view_args or {}).values():
            if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]{0,252}', name):
                return {'message': 'Invalid resource name'}, 400

    app.register_blueprint(routes, url_prefix='/rest/1.0')
    ui = Path(__file__).resolve().parents[2] / 'ui'

    @app.get('/ui/')
    def dashboard():
        return send_from_directory(ui, 'index.html')

    @app.get('/ui/dashboard.js')
    def dashboard_script():
        return send_from_directory(ui, 'dashboard.js')

    return app
