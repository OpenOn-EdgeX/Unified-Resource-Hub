from functools import lru_cache
from flask import current_app


@lru_cache(maxsize=4)
def _connection(filename):
    from kubernetes import client, config

    cfg = client.Configuration()
    if filename:
        config.load_kube_config(config_file=filename, client_configuration=cfg, persist_config=False)
    else:
        config.load_incluster_config(client_configuration=cfg)
    return client.ApiClient(cfg)


def _api(kind):
    from kubernetes import client

    return getattr(client, kind)(_connection(current_app.config['KUBECONFIG']))


def get_core_api():
    return _api('CoreV1Api')


def get_app_api():
    return _api('AppsV1Api')


def get_batch_api():
    return _api('BatchV1Api')


def get_custom_api():
    return _api('CustomObjectsApi')


def get_discovery_api():
    return _api('DiscoveryV1Api')


def get_version_api():
    return _api('VersionApi')


def get_storage_api():
    return _api('StorageV1Api')
