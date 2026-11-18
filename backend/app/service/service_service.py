from http import HTTPStatus
from app.repository import k8s_repo
from app.repository import prom_repo
from utils.parse_utils import format_bps
from utils.time_utils import format_relative_time
from utils.pod_utils import get_pod_info, DEFAULT_POD_INFO
from utils.event_utils import build_event_summary
from app.service.formatters.prom_chart import prom_range_to_chart
from app.query import service_query as sq
from app.exceptions import ApiException

_ALLOWED_TYPES = ("ClusterIP", "NodePort", "LoadBalancer")

def namespace_list():
    try:
        namespaces = k8s_repo.list_active_namespaces()
        namespace_list = ["all"]

        namespace_list.extend(n.metadata.name for n in namespaces)

        return {"namespace_list": namespace_list}

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch service namespace list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="SERVICE_NAMESPACE_LIST_FETCH_FAILED",
        ) from exc

def service_type_list():
    try:
        services = k8s_repo.list_services()

        types = sorted(set(s.spec.type for s in services if s.spec.type in _ALLOWED_TYPES))

        return {"service_type_list": ["all"] + types}

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch service type list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="SERVICE_TYPE_LIST_FETCH_FAILED",
        ) from exc

def service_status(namespace_name: str, service_type: str):
    try:

        ns = None if namespace_name == "all" else namespace_name
        services = k8s_repo.list_services(ns)
        services = _filter_services(services, service_type)

        ep_slices = k8s_repo.list_endpoint_slices(ns)
        health_map = _build_endpoint_health_map(ep_slices)

        total_services = len(services)

        failed = 0
        degraded = 0
        total_endpoints = 0
        unhealthy_endpoints = 0
        all_pod_names = set()

        for svc in services:
            svc_name = svc.metadata.name
            svc_ns = svc.metadata.namespace

            health = health_map.get(
                (svc_ns, svc_name),
                {"ready": 0, "not_ready": 0, "pods": []},
            )
            ready = health["ready"]
            not_ready = health["not_ready"]
            pods = health["pods"]
            all_pod_names.update(pods)

            total_ep = ready + not_ready
            total_endpoints += total_ep
            unhealthy_endpoints += not_ready

            status = _endpoint_status(ready, not_ready)
            if status == "Failed":
                failed += 1
            elif status == "Degraded":
                degraded += 1

        received = 0.0
        transmitted = 0.0

        if all_pod_names:
            pod_regex = "|".join(all_pod_names)
            rx_query, tx_query = _ntw_status_queries(namespace_name, pod_regex)

            received = prom_repo.instant(rx_query) or 0.0
            transmitted = prom_repo.instant(tx_query) or 0.0

        return {
            "total_services": total_services,
            "degraded": degraded,
            "failed": failed,
            "total_endpoints": total_endpoints,
            "unhealthy_endpoints": unhealthy_endpoints,
            "network_received": format_bps(received),
            "network_transmitted": format_bps(transmitted),
        }

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch service status",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="SERVICE_STATUS_FETCH_FAILED",
        ) from exc

def service_list(namespace_name: str, service_type: str):
    try:
        ns = None if namespace_name == "all" else namespace_name
        services = k8s_repo.list_services(ns)
        services = _filter_services(services, service_type)

        ep_slices = k8s_repo.list_endpoint_slices(ns)
        health_map = _build_endpoint_health_map(ep_slices)

        result = []
        for svc in services:
            name = svc.metadata.name
            svc_ns = svc.metadata.namespace
            svc_type = svc.spec.type
            cluster_ip = svc.spec.cluster_ip or "None"

            external_ip = _get_external_ip(svc)

            port_str = _format_service_ports(svc.spec.ports)

            age = format_relative_time(svc.metadata.creation_timestamp)

            health = health_map.get(
                (svc_ns, name),
                {"ready": 0, "not_ready": 0, "pods": []},
            )
            ready = health["ready"]
            not_ready = health["not_ready"]

            total_ep = ready + not_ready
            endpoints_str = f"{ready}/{total_ep}"

            status = _endpoint_status(ready, not_ready)

            result.append(
                {
                    "name": name,
                    "namespace": svc_ns,
                    "type": svc_type,
                    "cluster_ip": cluster_ip,
                    "external_ip": external_ip,
                    "ports": port_str,
                    "age": age,
                    "endpoints": endpoints_str,
                    "status": status,
                }
            )

        return result

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch service list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="SERVICE_LIST_FETCH_FAILED",
        ) from exc

def _service_network_chart(
    namespace_name: str,
    service_name: str,
    start_date: str,
    end_date: str,
    query_template: dict,
):
    ep_slices = k8s_repo.list_endpoint_slices_by_service(namespace_name, service_name)
    pod_names = sorted(set(_get_pod_names(ep_slices)))

    if not pod_names:
        return []

    pod_regex = "|".join(pod_names)
    query = query_template["query"].format(
        namespace=namespace_name,
        pod_regex=pod_regex,
    )

    result = prom_repo.history_auto_step(query, start_date, end_date)

    return prom_range_to_chart(
        result,
        label_key="_none_",
        default_name=service_name,
    )

def network_received(
    namespace_name: str, service_name: str, start_date: str, end_date: str
):
    try:
        return _service_network_chart(
            namespace_name,
            service_name,
            start_date,
            end_date,
            sq.NETWORK_RX_BY_SERVICE_1M,
        )

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch service network received",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="SERVICE_NETWORK_RECEIVED_FETCH_FAILED",
        ) from exc

def network_transmitted(
    namespace_name: str, service_name: str, start_date: str, end_date: str
):
    try:
        return _service_network_chart(
            namespace_name,
            service_name,
            start_date,
            end_date,
            sq.NETWORK_TX_BY_SERVICE_1M,
        )

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch service network transmitted",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="SERVICE_NETWORK_TRANSMITTED_FETCH_FAILED",
        ) from exc

def endpoint_list(namespace_name: str, service_name: str):
    try:
        ep_slices = k8s_repo.list_endpoint_slices_by_service(namespace_name, service_name)

        if not ep_slices:
            return []

        pods, sidecar_lookup = k8s_repo.list_pods_with_sidecar_lookup(
            namespace_name
        )
        target_pod_names = set(_get_pod_names(ep_slices))

        pod_info_map = {}
        if target_pod_names:
            for p in pods:
                if p.metadata.name not in target_pod_names:
                    continue

                sidecars = sidecar_lookup.get(p.metadata.uid, frozenset())
                pod_info_map[p.metadata.name] = get_pod_info(p, sidecar_names=sidecars)

        endpoints = []
        for eps in ep_slices:

            ports = eps.get("ports", [])
            port_str = _format_endpoint_ports(ports)

            for ep in eps.get("endpoints", []):

                addresses = ep.get("addresses", [])

                target_ref = ep.get("targetRef", {})
                pod_name = (
                    target_ref.get("name", "-") if target_ref.get("kind") == "Pod" else "-"
                )

                node_name = ep.get("nodeName", "-")

                _pod_info = pod_info_map.get(pod_name, DEFAULT_POD_INFO)

                for addr in addresses:
                    endpoints.append(
                        {
                            "endpoint_ip": addr,
                            "pod_name": pod_name,
                            "status": _pod_info["status"],
                            "ready": _pod_info["ready"],
                            "node": node_name,
                            "port": port_str,
                        }
                    )

        return endpoints

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch service endpoint list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="SERVICE_ENDPOINT_LIST_FETCH_FAILED",
        ) from exc

def events(namespace_name: str, service_name: str):
    try:
        raw = k8s_repo.list_events_by_service(namespace_name, service_name)
        return build_event_summary(raw)

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch service events",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="SERVICE_EVENTS_FETCH_FAILED",
        ) from exc

def _filter_services(services, service_type):
    if service_type == "all":
        return [s for s in services if s.spec.type in _ALLOWED_TYPES]
    return [s for s in services if s.spec.type == service_type]

def _build_endpoint_health_map(ep_slices):
    health_map = {}

    for eps in ep_slices:
        meta = eps.get("metadata", {})
        ns = meta.get("namespace", "")

        labels = meta.get("labels", {})
        svc = labels.get("kubernetes.io/service-name")

        if not svc:
            continue

        key = (ns, svc)

        if key not in health_map:
            health_map[key] = {
                "ready": 0,
                "not_ready": 0,
                "pods": set(),
            }

        for ep in eps.get("endpoints", []):

            conditions = ep.get("conditions", {})

            is_ready = conditions.get("ready")
            is_terminating = conditions.get("terminating", False)

            if is_ready and not is_terminating:
                health_map[key]["ready"] += 1
            else:
                health_map[key]["not_ready"] += 1

            ref = ep.get("targetRef", {})
            if ref.get("kind") == "Pod":
                name = ref.get("name")
                if name:
                    health_map[key]["pods"].add(name)

    for v in health_map.values():
        v["pods"] = list(v["pods"])

    return health_map

def _endpoint_status(ready, not_ready):
    total = ready + not_ready
    if total == 0 or ready == 0:
        return "Failed"
    if not_ready > 0:
        return "Degraded"
    return "Healthy"

def _get_external_ip(svc):
    external_ips = getattr(svc.spec, "external_i_ps", None) or []

    return ", ".join(str(ip) for ip in external_ips) if external_ips else "<none>"

def _get_pod_names(ep_slices):
    pod_names = []

    for eps in ep_slices:
        for ep in eps.get("endpoints", []):
            ref = ep.get("targetRef", {})
            if ref.get("kind") == "Pod" and ref.get("name"):
                pod_names.append(ref["name"])

    return pod_names

def _format_service_ports(ports):
    if not ports:
        return "<none>"

    formatted = []
    for p in ports:
        if p.node_port:

            formatted.append(f"{p.port}:{p.node_port}/{p.protocol}")
        else:

            formatted.append(f"{p.port}/{p.protocol}")

    return ", ".join(formatted)

def _format_endpoint_ports(ports):
    if not ports:
        return "<none>"

    formatted = []
    for p in ports:
        if p.get("port") is not None:

            formatted.append(f"{p.get('port')}/{p.get('protocol', 'TCP')}")

    return ", ".join(formatted)

def _ntw_status_queries(namespace_name, pod_regex):
    if namespace_name == "all":
        rx_query = sq.NETWORK_RX_STATUS_ALL_5M["query"].format(pod_regex=pod_regex)
        tx_query = sq.NETWORK_TX_STATUS_ALL_5M["query"].format(pod_regex=pod_regex)
    else:
        rx_query = sq.NETWORK_RX_STATUS_NS_5M["query"].format(
            namespace=namespace_name,
            pod_regex=pod_regex,
        )
        tx_query = sq.NETWORK_TX_STATUS_NS_5M["query"].format(
            namespace=namespace_name,
            pod_regex=pod_regex,
        )

    return rx_query, tx_query
