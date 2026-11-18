from http import HTTPStatus

from app.repository import k8s_repo
from app.exceptions import ApiException

from app.repository.prom_repo import instant, last_hour, history
from app.query import cluster_query as cq
from app.query import gpu_query as gq
from utils.parse_utils import parse_usage, to_display_value
from utils.event_utils import build_event_summary

def nodes():
    try:
        nodes = k8s_repo.list_nodes()

        avg = history(cq.NODE_READY_COUNT["query"])
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch dashboard node summary",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DASHBOARD_NODES_FETCH_FAILED",
        ) from exc

    ready_nodes = [
        n for n in nodes
        if any(c.type == "Ready" and c.status == "True" for c in n.status.conditions)
    ]

    return {
        "total_nodes": len(nodes),
        "ready_nodes": len(ready_nodes),
        "data": avg
    }

def namespaces():
    try:
        active_ns = k8s_repo.list_active_namespaces()

        avg = history(cq.NAMESPACE_ACTIVE_COUNT["query"])
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch dashboard namespace summary",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DASHBOARD_NAMESPACES_FETCH_FAILED",
        ) from exc

    return {
        "total_namespaces": len(active_ns),
        "data": avg
    }

def pods():
    try:
        pods = k8s_repo.list_pods()

        avg = history(cq.POD_RUNNING_COUNT["query"])
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch dashboard pod summary",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DASHBOARD_PODS_FETCH_FAILED",
        ) from exc

    running_pods = [p for p in pods if p.status.phase == "Running"]

    return {
        "total_pods": len(pods),
        "running_pods": len(running_pods),
        "data": avg
    }

def workloads():
    try:
        dep = k8s_repo.list_deployments()
        sts = k8s_repo.list_statefulsets()
        dms = k8s_repo.list_daemonsets()

        ready_dep = [d for d in dep if d.status.ready_replicas == d.spec.replicas]
        ready_sts = [s for s in sts if s.status.ready_replicas == s.spec.replicas]
        ready_dms = [d for d in dms if d.status.number_ready == d.status.desired_number_scheduled]

        total = len(dep + sts + dms)
        ready = len(ready_dep + ready_sts + ready_dms)

        avg = history(cq.WORKLOAD_READY_COUNT["query"])
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch dashboard workload summary",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DASHBOARD_WORKLOADS_FETCH_FAILED",
        ) from exc

    return {
        "total_workloads": total,
        "ready_workloads": ready,
        "data": avg
    }

def services():
    try:
        services = k8s_repo.list_services()
        endpoint_slices = k8s_repo.list_endpoint_slices()
        target_service_types = {"ClusterIP", "NodePort", "LoadBalancer"}
        target_services = [svc for svc in services if svc.spec.type in target_service_types]

        total_services = len(target_services)

        avg_data = history(cq.SERVICE_COUNT["query"])

        service_health_map = {}

        for es in endpoint_slices:
            metadata = es.get("metadata", {})
            labels = metadata.get("labels", {})

            svc_name = labels.get("kubernetes.io/service-name")
            ns = metadata.get("namespace")

            if not svc_name or not ns:
                continue

            key = (ns, svc_name)
            if key not in service_health_map:
                service_health_map[key] = {"ready": 0, "not_ready": 0}

            for ep in es.get("endpoints", []):
                conditions = ep.get("conditions", {})
                is_ready = conditions.get("ready")
                is_terminating = conditions.get("terminating", False)

                if is_ready and not is_terminating:
                    service_health_map[key]["ready"] += 1
                else:
                    service_health_map[key]["not_ready"] += 1

        ready_count = 0
        for svc in target_services:
            svc_ns = svc.metadata.namespace
            svc_name = svc.metadata.name
            key = (svc_ns, svc_name)
            health = service_health_map.get(key, {"ready": 0, "not_ready": 0})
            if health["ready"] > 0 and health["not_ready"] == 0:
                ready_count += 1
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch dashboard service summary",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DASHBOARD_SERVICES_FETCH_FAILED",
        ) from exc

    return {
        "total_services": total_services,
        "endpoints_services": ready_count,
        "data": avg_data
    }

def resource_usage():
    try:
        cpu_ratio = instant(cq.CLUSTER_CPU_USAGE_5M["query"]) or 0
        mem_ratio = instant(cq.CLUSTER_MEM_USAGE_CURRENT["query"]) or 0
        disk_ratio = instant(cq.CLUSTER_DISK_USAGE_CURRENT["query"]) or 0

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch dashboard resource usage",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DASHBOARD_RESOURCE_USAGE_FETCH_FAILED",
        ) from exc

    return {
        "cpu_usage": round(cpu_ratio * 100, 2),
        "memory_usage": round(mem_ratio * 100, 2),
        "disk_usage": round(disk_ratio * 100, 2),
    }

def gpu_usage():
    results = {}

    GPU_KEY_MAP = {
        "GPU_UTIL_AVG_5M": "Compute",
        "GPU_MEM_COPY_UTIL_AVG_5M": "Memory",
        "GPU_ENC_UTIL_AVG_5M": "Encode",
        "GPU_DEC_UTIL_AVG_5M": "Decode",
    }

    try:
        for key in GPU_KEY_MAP:
            cfg = getattr(gq, key)
            val = instant(cfg["query"])
            results[GPU_KEY_MAP[key]] = round(val, 2) if val else 0.0
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch dashboard GPU usage",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DASHBOARD_GPU_USAGE_FETCH_FAILED",
        ) from exc

    return results

def disk_io():
    try:
        result = {
            "read": last_hour(cq.CLUSTER_DISK_READ_5M["query"]),
            "write": last_hour(cq.CLUSTER_DISK_WRITE_5M["query"])
        }
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch dashboard disk IO",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DASHBOARD_DISK_IO_FETCH_FAILED",
        ) from exc

    return result

def network_io():
    try:
        result = {
            "received": last_hour(cq.CLUSTER_NET_RECV_5M["query"]),
            "transmitted": last_hour(cq.CLUSTER_NET_TRANS_5M["query"])
        }
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch dashboard network IO",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DASHBOARD_NETWORK_IO_FETCH_FAILED",
        ) from exc

    return result

def cpu_top_5():
    try:
        result = get_usage("cpu")
    except ApiException:
        raise
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch dashboard CPU top 5",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DASHBOARD_CPU_TOP_FETCH_FAILED",
        ) from exc

    return result

def memory_top_5():
    try:
        result = get_usage("memory")
    except ApiException:
        raise
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch dashboard memory top 5",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DASHBOARD_MEMORY_TOP_FETCH_FAILED",
        ) from exc

    return result

def get_usage(resource_type):
    metrics = k8s_repo.list_pod_metrics()
    results = []

    for m in metrics:
        ns = m["metadata"]["namespace"]
        pod = m["metadata"]["name"]

        if ns in k8s_repo.system_ns:
            continue

        total_usage = sum(
            parse_usage(resource_type, c["usage"].get(resource_type, "0"))
            for c in m.get("containers", [])
        )

        if total_usage <= 0:
            continue

        pod_spec = k8s_repo.get_pod_resources(pod, ns)
        resource_info = calculate_resources(pod_spec, resource_type)

        results.append({
            "pod_name": pod,
            f"{resource_type}_usage": to_display_value(resource_type, total_usage),
            f"{resource_type}_limit": to_display_value(resource_type, resource_info["limit"]),
            f"{resource_type}_request": to_display_value(resource_type, resource_info["request"]),
        })

    return sorted(
        results,
        key=lambda x: x[f"{resource_type}_usage"],
        reverse=True
    )[:5]

def calculate_resources(pod_spec, resource_type):
    total_limit = 0
    total_request = 0
    init_limits = []
    init_requests = []

    for c in pod_spec.spec.containers:
        total_limit += parse_usage(
            resource_type, (c.resources.limits or {}).get(resource_type, "0")
        )
        total_request += parse_usage(
            resource_type, (c.resources.requests or {}).get(resource_type, "0")
        )

    if pod_spec.spec.init_containers:
        for ic in pod_spec.spec.init_containers:
            init_limits.append(
                parse_usage(resource_type, (ic.resources.limits or {}).get(resource_type, "0"))
            )
            init_requests.append(
                parse_usage(resource_type, (ic.resources.requests or {}).get(resource_type, "0"))
            )

        return {
            "limit": max(total_limit, max(init_limits, default=0)),
            "request": max(total_request, max(init_requests, default=0)),
        }

    return {
        "limit": total_limit,
        "request": total_request,
    }

def events():
    try:
        events = k8s_repo.list_events()
        result = build_event_summary(events, include_namespace=True)
    except ApiException:
        raise
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch dashboard events",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="DASHBOARD_EVENTS_FETCH_FAILED",
        ) from exc

    return result
