from http import HTTPStatus
from app.repository import k8s_repo
from app.repository import prom_repo
from utils.parse_utils import format_bytes_iec
from utils.parse_utils import format_bytes_si
from utils.parse_utils import format_number
from utils.time_utils import format_relative_time
from utils.pod_utils import get_pod_info, build_pod_metric_map
from app.service.formatters.prom_chart import prom_range_to_chart
from app.query import pod_query as pq
from app.query import cluster_query as cq
from app.query import node_query as nq
from app.exceptions import ApiException

def namespace_list():
    try:
        namespaces = k8s_repo.list_active_namespaces()
        namespace_list = ["all"]
        namespace_list.extend(n.metadata.name for n in namespaces)

        return {"namespace_list": namespace_list}

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch pod namespace list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="POD_NAMESPACE_LIST_FETCH_FAILED",
        ) from exc

def node_list():
    try:
        nodes = k8s_repo.list_nodes()
        node_list = ["all"]

        node_list.extend(n.metadata.name for n in nodes)

        return {"node_list": node_list}

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch pod node list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="POD_NODE_LIST_FETCH_FAILED",
        ) from exc

def pod_status(namespace_name: str, node_name: str):
    try:
        ns = None if namespace_name == "all" else namespace_name
        pods = k8s_repo.list_pods(ns)

        total_pods = 0
        running_pods = 0
        pending_pods = 0
        failed_pods = 0
        completed_pods = 0

        for pod in pods:

            if node_name != "all" and pod.spec.node_name != node_name:
                continue

            phase = pod.status.phase

            total_pods += 1

            if phase == "Running":
                running_pods += 1
            elif phase == "Pending":
                pending_pods += 1
            elif phase in ("Failed", "Unknown"):

                failed_pods += 1
            elif phase == "Succeeded":
                completed_pods += 1

        if node_name == "all":
            total_cpu = prom_repo.instant(cq.CLUSTER_CPU_TOTAL_CURRENT["query"]) or 0.0
            total_mem = prom_repo.instant(cq.CLUSTER_MEM_TOTAL_CURRENT["query"]) or 0.0
        else:
            total_cpu = (
                prom_repo.instant(nq.NODE_CPU_TOTAL_CURRENT["query"] % node_name) or 0.0
            )
            total_mem = (
                prom_repo.instant(nq.NODE_MEM_TOTAL_CURRENT["query"] % node_name) or 0.0
            )

        used_cpu, used_mem = resource_usage(namespace_name, node_name)

        return {
            "total_pods": total_pods,
            "running_pods": running_pods,
            "pending_pods": pending_pods,
            "failed_pods": failed_pods,
            "completed_pods": completed_pods,
            "cpu_usage": f"{format_number(used_cpu)} / {format_number(total_cpu)} cores",
            "memory_usage": f"{format_bytes_iec(used_mem)} / {format_bytes_iec(total_mem)}",
        }

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch pod status",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="POD_STATUS_FETCH_FAILED",
        ) from exc

def resource_usage(namespace_name: str, node_name: str):
    cpu_query = _select_query(
        namespace_name,
        node_name,
        pq.POD_TOTAL_CPU_USAGE_ALL_5M,
        pq.POD_TOTAL_CPU_USAGE_BY_NS_5M,
        pq.POD_TOTAL_CPU_USAGE_BY_NODE_5M,
        pq.POD_TOTAL_CPU_USAGE_BY_NODE_AND_NS_5M,
    )
    mem_query = _select_query(
        namespace_name,
        node_name,
        pq.POD_TOTAL_MEMORY_USAGE_ALL,
        pq.POD_TOTAL_MEMORY_USAGE_BY_NS,
        pq.POD_TOTAL_MEMORY_USAGE_BY_NODE,
        pq.POD_TOTAL_MEMORY_USAGE_BY_NODE_AND_NS,
    )

    used_cpu = prom_repo.instant(cpu_query) or 0.0
    used_mem = prom_repo.instant(mem_query) or 0.0

    return used_cpu, used_mem

def cpu_usage(namespace_name: str, node_name: str, start_date: str, end_date: str):
    try:
        query = _select_query(
            namespace_name,
            node_name,
            pq.CPU_USAGE_BY_POD_ALL_5M,
            pq.CPU_USAGE_BY_POD_NS_5M,
            pq.CPU_USAGE_BY_POD_NODE_5M,
            pq.CPU_USAGE_BY_POD_NODE_AND_NS_5M,
        )
        result = prom_repo.history_auto_step(query, start_date, end_date)

        return prom_range_to_chart(
            result,
            label_key="pod",
            default_name="unknown_pod",
            round_digits=5,
        )

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch pod cpu usage",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="POD_CPU_USAGE_FETCH_FAILED",
        ) from exc

def memory_usage(namespace_name: str, node_name: str, start_date: str, end_date: str):
    try:
        query = _select_query(
            namespace_name,
            node_name,
            pq.MEMORY_USAGE_BY_POD_ALL,
            pq.MEMORY_USAGE_BY_POD_NS,
            pq.MEMORY_USAGE_BY_POD_NODE,
            pq.MEMORY_USAGE_BY_POD_NODE_AND_NS,
        )
        result = prom_repo.history_auto_step(query, start_date, end_date)

        return prom_range_to_chart(
            result,
            label_key="pod",
            default_name="unknown_pod",
        )

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch pod memory usage",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="POD_MEMORY_USAGE_FETCH_FAILED",
        ) from exc

def network_received(
    namespace_name: str, node_name: str, start_date: str, end_date: str
):
    try:
        query = _select_query(
            namespace_name,
            node_name,
            pq.NETWORK_RX_BY_POD_ALL_1M,
            pq.NETWORK_RX_BY_POD_NS_1M,
            pq.NETWORK_RX_BY_POD_NODE_1M,
            pq.NETWORK_RX_BY_POD_NODE_AND_NAMESPACE_1M,
        )
        result = prom_repo.history_auto_step(query, start_date, end_date)

        return prom_range_to_chart(
            result,
            label_key="pod",
            default_name="unknown_pod",
        )

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch pod network received",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="POD_NETWORK_RECEIVED_FETCH_FAILED",
        ) from exc

def network_transmitted(
    namespace_name: str, node_name: str, start_date: str, end_date: str
):
    try:
        query = _select_query(
            namespace_name,
            node_name,
            pq.NETWORK_TX_BY_POD_ALL_1M,
            pq.NETWORK_TX_BY_POD_NS_1M,
            pq.NETWORK_TX_BY_POD_NODE_1M,
            pq.NETWORK_TX_BY_POD_NODE_AND_NS_1M,
        )
        result = prom_repo.history_auto_step(query, start_date, end_date)

        return prom_range_to_chart(
            result,
            label_key="pod",
            default_name="unknown_pod",
        )

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch pod network transmitted",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="POD_NETWORK_TRANSMITTED_FETCH_FAILED",
        ) from exc

def pod_list(namespace_name: str, node_name: str):
    try:
        ns = None if namespace_name == "all" else namespace_name
        metrics = k8s_repo.list_pod_metrics(ns)

        field_selector = None if node_name == "all" else f"spec.nodeName={node_name}"

        pods, sidecar_lookup = k8s_repo.list_pods_with_sidecar_lookup(
            namespace=ns,
            field_selector=field_selector,
        )

        pod_metric_map = build_pod_metric_map(metrics)

        pod_list = []

        for pod in pods:

            if node_name != "all" and pod.spec.node_name != node_name:
                continue

            pod_name = pod.metadata.name

            pod_ns = pod.metadata.namespace

            pod_node = pod.spec.node_name or "<none>"

            sidecars = sidecar_lookup.get(pod.metadata.uid, frozenset())
            pod_info = get_pod_info(pod, sidecar_names=sidecars)

            status = pod_info["status"]

            ready_str = pod_info["ready"]

            restarts = pod_info["restarts"]

            last_restart_at = pod_info["last_restart_at"]
            if restarts > 0 and last_restart_at:
                restarts_str = (
                    f"{restarts} ({format_relative_time(last_restart_at)} ago)"
                )
            else:
                restarts_str = str(restarts)

            age = format_relative_time(pod.metadata.creation_timestamp)

            metric = pod_metric_map.get((pod_ns, pod_name), {})
            cpu = metric.get("cpu")
            mem = metric.get("memory")

            pod_list.append(
                {
                    "name": pod_name,
                    "namespace": pod_ns,
                    "status": status,
                    "ready": ready_str,
                    "restarts": restarts_str,
                    "age": age,
                    "cpu": cpu,
                    "memory": format_bytes_iec(mem) if mem is not None else None,
                    "node": pod_node,
                }
            )

        return pod_list

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch pod list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="POD_LIST_FETCH_FAILED",
        ) from exc

def _select_query(namespace_name, node_name, q_all, q_ns, q_node, q_both):
    ns = namespace_name
    node = node_name

    if ns == "all" and node == "all":
        return q_all["query"].format()
    elif ns != "all" and node == "all":
        return q_ns["query"].format(namespace=ns)
    elif ns == "all" and node != "all":
        return q_node["query"].format(node=node)
    else:
        return q_both["query"].format(node=node, namespace=ns)
