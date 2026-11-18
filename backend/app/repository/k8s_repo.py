from flask import current_app
from app.client.k8s_client import (
    get_version_api,
    get_core_api,
    get_discovery_api,
    get_app_api,
    get_batch_api,
    get_custom_api,
    get_storage_api,
)
from typing import Optional
import json

system_ns = ["kube-system", "kube-public", "kube-node-lease"]

CONTROL_PLANE_COMPONENTS = {
    "kube-apiserver": "API Server",
    "kube-scheduler": "Scheduler",
    "kube-controller-manager": "Controller Manager",
    "etcd": "Etcd",
}

def list_pod_metrics(namespace: Optional[str] = None):
    api = get_custom_api()

    if namespace:
        result = api.list_namespaced_custom_object(
            group="metrics.k8s.io",
            version="v1beta1",
            namespace=namespace,
            plural="pods",
        )
    else:
        result = api.list_cluster_custom_object(
            group="metrics.k8s.io", version="v1beta1", plural="pods"
        )

    return result["items"]

def get_cluster_name():
    return current_app.config.get('CLUSTER_NAME') or 'Kubernetes'

def get_cluster_version():
    try:
        v = get_version_api().get_code()
        return v.git_version
    except Exception:
        return None

def list_services(namespace: Optional[str] = None):
    core = get_core_api()

    if namespace:
        return core.list_namespaced_service(namespace=namespace).items
    else:
        return core.list_service_for_all_namespaces().items

def list_endpoint_slices(namespace: Optional[str] = None):
    api = get_discovery_api()

    if namespace:
        raw = api.list_namespaced_endpoint_slice(
            namespace=namespace,
            _preload_content=False,
        )
    else:
        raw = api.list_endpoint_slice_for_all_namespaces(_preload_content=False)

    data = json.loads(raw.data.decode("utf-8"))
    items = data.get("items", [])
    valid = [item for item in items if item.get("endpoints")]

    return valid

def list_nodes():
    return get_core_api().list_node().items

def list_namespaces():
    return get_core_api().list_namespace().items

def list_active_namespaces():
    namespaces = list_namespaces()
    return [n for n in namespaces if getattr(n.status, "phase", None) == "Active"]

def list_pods(namespace: Optional[str] = None, label_selector: Optional[str] = None):
    core = get_core_api()

    kwargs = {"label_selector": label_selector} if label_selector else {}

    if namespace:
        return core.list_namespaced_pod(namespace=namespace, **kwargs).items
    else:
        return core.list_pod_for_all_namespaces(**kwargs).items

def list_pods_with_sidecar_lookup(
    namespace: Optional[str] = None,
    field_selector: Optional[str] = None,
):

    core = get_core_api()

    resp = _list_pods_raw(core, namespace=namespace, field_selector=field_selector)
    pod_list = core.api_client.deserialize(resp, "V1PodList")

    return pod_list.items or [], _build_sidecar_lookup(resp.data)

def list_pods_by_node_with_sidecar_lookup(node_name: str):

    return list_pods_with_sidecar_lookup(field_selector=f"spec.nodeName={node_name}")

def _list_pods_raw(
    core,
    namespace: Optional[str] = None,
    field_selector: Optional[str] = None,
):
    kwargs = {"_preload_content": False}
    if field_selector:
        kwargs["field_selector"] = field_selector

    if namespace:
        return core.list_namespaced_pod(namespace=namespace, **kwargs)

    return core.list_pod_for_all_namespaces(**kwargs)

def _build_sidecar_lookup(raw_data: bytes) -> dict:
    data = json.loads(raw_data.decode("utf-8"))
    lookup = {}

    for item in data.get("items", []):
        uid = item.get("metadata", {}).get("uid")
        if not uid:
            continue
        sidecars = {
            c.get("name")
            for c in (item.get("spec", {}).get("initContainers") or [])
            if c.get("name") and c.get("restartPolicy") == "Always"
        }
        if sidecars:
            lookup[uid] = sidecars

    return lookup

def list_deployments(
    namespace: Optional[str] = None, label_selector: Optional[str] = None
):
    app = get_app_api()
    kwargs = {"label_selector": label_selector} if label_selector else {}

    if namespace:
        return app.list_namespaced_deployment(namespace=namespace, **kwargs).items
    else:
        return app.list_deployment_for_all_namespaces(**kwargs).items

def list_statefulsets(namespace: Optional[str] = None):
    app = get_app_api()

    if namespace:
        return app.list_namespaced_stateful_set(namespace=namespace).items
    else:
        return app.list_stateful_set_for_all_namespaces().items

def list_daemonsets(namespace: Optional[str] = None):
    app = get_app_api()

    if namespace:
        return app.list_namespaced_daemon_set(namespace=namespace).items
    else:
        return app.list_daemon_set_for_all_namespaces().items

def list_replica_sets(namespace: Optional[str] = None):
    app = get_app_api()

    if namespace:
        return app.list_namespaced_replica_set(namespace=namespace).items
    else:
        return app.list_replica_set_for_all_namespaces().items

def list_jobs(namespace: Optional[str] = None):
    batch = get_batch_api()

    if namespace:
        return batch.list_namespaced_job(namespace=namespace).items
    else:
        return batch.list_job_for_all_namespaces().items

def list_events(namespace: Optional[str] = None):
    core = get_core_api()

    if namespace:
        return core.list_namespaced_event(namespace=namespace).items
    else:
        return core.list_event_for_all_namespaces().items

def get_pod_resources(pod_name, namespace):
    core = get_core_api()
    return core.read_namespaced_pod(pod_name, namespace)

def get_node(node_name: str):
    return get_core_api().read_node(name=node_name)

def list_endpoint_slices_by_service(namespace, service_name):
    api = get_discovery_api()

    raw = api.list_namespaced_endpoint_slice(
        namespace=namespace,
        label_selector=f"kubernetes.io/service-name={service_name}",
        _preload_content=False,
    )
    data = json.loads(raw.data.decode("utf-8"))
    items = data.get("items", [])
    valid = [item for item in items if item.get("endpoints")]

    return valid

def list_events_by_service(namespace, service_name):
    core = get_core_api()

    raw = core.list_namespaced_event(
        namespace=namespace,
        field_selector=f"involvedObject.kind=Service,involvedObject.name={service_name}",
    ).items

    return raw

def list_pvcs(namespace: Optional[str] = None):
    core = get_core_api()

    if namespace:
        return core.list_namespaced_persistent_volume_claim(namespace=namespace).items
    else:
        return core.list_persistent_volume_claim_for_all_namespaces().items

def get_pvc(namespace: str, pvc_name: str):
    return get_core_api().read_namespaced_persistent_volume_claim(
        name=pvc_name,
        namespace=namespace,
    )

def list_pvs():
    return get_core_api().list_persistent_volume().items

def get_pv(pv_name: str):
    return get_core_api().read_persistent_volume(name=pv_name)

def list_storage_classes():
    return get_storage_api().list_storage_class().items

def list_events_by_pvc(namespace, pvc_name):
    core = get_core_api()

    raw = core.list_namespaced_event(
        namespace=namespace,
        field_selector=f"involvedObject.kind=PersistentVolumeClaim,involvedObject.name={pvc_name}",
    ).items

    return raw
