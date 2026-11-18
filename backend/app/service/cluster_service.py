from http import HTTPStatus
from app.repository import k8s_repo
from app.repository import prom_repo

from app.query import cluster_query as cq
from app.query import namespace_query as nq

from utils.parse_utils import format_bytes_iec
from utils.parse_utils import format_bytes_si
from utils.parse_utils import format_bytes_per_sec_iec
from utils.parse_utils import format_iops_per_sec
from utils.event_utils import build_event_summary
from utils.pod_utils import get_pod_info
from utils.time_utils import format_relative_time
from app.service.formatters.prom_chart import prom_range_to_chart
from app.exceptions import ApiException

def cluster_status():
    try:
        cluster_name = k8s_repo.get_cluster_name() or "-"
        cluster_version = k8s_repo.get_cluster_version() or "-"

        cluster_status = "Normal"
        control_plane_component = []

        pods, sidecar_lookup = k8s_repo.list_pods_with_sidecar_lookup(
            namespace="kube-system"
        )

        for pod in pods:
            pod_name = pod.metadata.name

            if not any(
                pod_name.startswith(prefix)
                for prefix in k8s_repo.CONTROL_PLANE_COMPONENTS.keys()
            ):
                continue

            sidecars = sidecar_lookup.get(pod.metadata.uid, frozenset())
            pod_info = get_pod_info(pod, sidecar_names=sidecars)
            pod_status = pod_info["status"]
            ready = pod_info["ready"]

            if pod_status != "Running":
                cluster_status = "Error"

            control_plane_component.append({
                "pod_name": pod_name,
                "ready": ready,
                "status": pod_status,
            })

        nodes = k8s_repo.list_nodes()

        node_items = []
        ready_node_count = 0

        for n in nodes:

            ready_condition = next(
                (c for c in n.status.conditions if c.type == "Ready"),
                None
            )

            is_ready = ready_condition and ready_condition.status == "True"

            if is_ready:
                ready_node_count += 1

            if ready_condition is None:
                status = "Unknown"
            else:
                status = "Ready" if is_ready else "NotReady"

            if status != "Ready":
                cluster_status = "Error"

            created_at = n.metadata.creation_timestamp
            age = format_relative_time(created_at)
            version = n.status.node_info.kubelet_version

            node_items.append({
                "name": n.metadata.name,
                "status": status,
                "age": age,
                "version": version,
            })

        total_cpu = prom_repo.instant(cq.CLUSTER_CPU_TOTAL_CURRENT["query"]) or 0
        total_memory_bytes = prom_repo.instant(cq.CLUSTER_MEM_TOTAL_CURRENT["query"]) or 0
        total_disk_bytes = prom_repo.instant(cq.CLUSTER_DISK_TOTAL_CURRENT["query"]) or 0

        return {
            "cluster_status": cluster_status,
            "cluster_name": cluster_name,
            "cluster_version": cluster_version,
            "control_plane_component": control_plane_component,
            "total_nodes": len(nodes),
            "ready_nodes": ready_node_count,
            "node_info": node_items,
            "total_cpu": f"{int(total_cpu)} cores",
            "total_memory": format_bytes_si(total_memory_bytes, 0),
            "total_disk": format_bytes_si(total_disk_bytes, 0),
        }
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch cluster status",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="CLUSTER_STATUS_FETCH_FAILED",
        ) from exc

def utilization():
    try:
        cpu_ratio = prom_repo.instant(cq.CLUSTER_CPU_USAGE_5M["query"]) or 0
        mem_ratio = prom_repo.instant(cq.CLUSTER_MEM_USAGE_CURRENT["query"]) or 0

        return {
            "cpu_utilization": round(cpu_ratio * 100, 2),
            "memory_utilization": round(mem_ratio * 100, 2),
        }
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch cluster utilization",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="CLUSTER_UTILIZATION_FETCH_FAILED",
        ) from exc

def cpu_usage_by_namespace(start_date: str, end_date: str):
    try:
        result = prom_repo.history_auto_step(nq.NAMESPACE_CPU_USAGE_5M["query"], start_date, end_date)
        return prom_range_to_chart(result, round_digits=5)
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch cluster cpu usage by namespace",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="CLUSTER_CPU_USAGE_BY_NAMESPACE_FETCH_FAILED",
        ) from exc

def memory_usage_by_namespace(start_date: str, end_date: str):
    try:
        result = prom_repo.history_auto_step(nq.NAMESPACE_MEMORY_USAGE_CURRENT["query"], start_date, end_date)
        return prom_range_to_chart(result)
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch cluster memory usage by namespace",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="CLUSTER_MEMORY_USAGE_BY_NAMESPACE_FETCH_FAILED",
        ) from exc

def network_rx_by_namespace(start_date: str, end_date: str):
    try:
        result = prom_repo.history_auto_step(nq.NAMESPACE_NETWORK_RX_RATE_5M["query"], start_date, end_date)
        return prom_range_to_chart(result)
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch cluster network rx by namespace",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="CLUSTER_NETWORK_RX_BY_NAMESPACE_FETCH_FAILED",
        ) from exc

def network_tx_by_namespace(start_date: str, end_date: str):
    try:
        result = prom_repo.history_auto_step(nq.NAMESPACE_NETWORK_TX_RATE_5M["query"], start_date, end_date)
        return prom_range_to_chart(result)
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch cluster network tx by namespace",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="CLUSTER_NETWORK_TX_BY_NAMESPACE_FETCH_FAILED",
        ) from exc

def disk_iops_by_namespace(start_date: str, end_date: str):
    try:
        result = prom_repo.history_auto_step(nq.NAMESPACE_DISK_IOPS_RATE_5M["query"], start_date, end_date)
        return prom_range_to_chart(result)
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch cluster disk iops by namespace",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="CLUSTER_DISK_IOPS_BY_NAMESPACE_FETCH_FAILED",
        ) from exc

def disk_throughput_by_namespace(start_date: str, end_date: str):
    try:
        result = prom_repo.history_auto_step(nq.NAMESPACE_DISK_THROUGHPUT_RATE_5M["query"], start_date, end_date)
        return prom_range_to_chart(result)
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch cluster disk throughput by namespace",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="CLUSTER_DISK_THROUGHPUT_BY_NAMESPACE_FETCH_FAILED",
        ) from exc

def summary_by_namespace():
    try:

        summary_map = {
            ns.metadata.name: {
                "namespace": ns.metadata.name,
                "pods": 0,
                "workloads": 0,
                "services": 0,
                "cpu_usage": None,
                "memory_usage": None,
                "received_bw": None,
                "transmitted_bw": None,
                "disk_iops": None,
                "disk_throughput": None,
            }
            for ns in k8s_repo.list_namespaces()
        }

        for pod in k8s_repo.list_pods():
            ns = pod.metadata.namespace
            if ns in summary_map:
                summary_map[ns]["pods"] += 1

        for dep in k8s_repo.list_deployments():
            ns = dep.metadata.namespace
            if ns in summary_map:
                summary_map[ns]["workloads"] += 1

        for dms in k8s_repo.list_daemonsets():
            ns = dms.metadata.namespace
            if ns in summary_map:
                summary_map[ns]["workloads"] += 1

        for sts in k8s_repo.list_statefulsets():
            ns = sts.metadata.namespace
            if ns in summary_map:
                summary_map[ns]["workloads"] += 1

        for svc in k8s_repo.list_services():
            ns = svc.metadata.namespace
            if ns in summary_map:
                summary_map[ns]["services"] += 1

        active_ns = set()

        result = prom_repo.instant_series(nq.NAMESPACE_CPU_USAGE_5M["query"])

        if result.get("status") == "success":
            for item in result.get("data", {}).get("result", []):
                ns = item.get("metric", {}).get("namespace")
                if not ns or ns not in summary_map:
                    continue

                try:
                    value = float(item.get("value", [None, "0"])[1])
                except (ValueError, TypeError):
                    value = 0.0

                summary_map[ns]["cpu_usage"] = round(value, 4)
                active_ns.add(ns)

        result = prom_repo.instant_series(nq.NAMESPACE_MEMORY_USAGE_CURRENT["query"])

        if result.get("status") == "success":
            for item in result.get("data", {}).get("result", []):
                ns = item.get("metric", {}).get("namespace")
                if not ns or ns not in summary_map:
                    continue

                try:
                    value = float(item.get("value", [None, "0"])[1])
                except (ValueError, TypeError):
                    value = 0.0

                summary_map[ns]["memory_usage"] = format_bytes_iec(value, 1)
                active_ns.add(ns)

        result = prom_repo.instant_series(nq.NAMESPACE_NETWORK_RX_RATE_5M["query"])

        if result.get("status") == "success":
            for item in result.get("data", {}).get("result", []):
                ns = item.get("metric", {}).get("namespace")
                if not ns or ns not in summary_map:
                    continue

                try:
                    value = float(item.get("value", [None, "0"])[1])
                except (ValueError, TypeError):
                    value = 0.0

                summary_map[ns]["received_bw"] = format_bytes_per_sec_iec(value)
                active_ns.add(ns)

        result = prom_repo.instant_series(nq.NAMESPACE_NETWORK_TX_RATE_5M["query"])

        if result.get("status") == "success":
            for item in result.get("data", {}).get("result", []):
                ns = item.get("metric", {}).get("namespace")
                if not ns or ns not in summary_map:
                    continue

                try:
                    value = float(item.get("value", [None, "0"])[1])
                except (ValueError, TypeError):
                    value = 0.0

                summary_map[ns]["transmitted_bw"] = format_bytes_per_sec_iec(value)
                active_ns.add(ns)

        result = prom_repo.instant_series(nq.NAMESPACE_DISK_IOPS_RATE_5M["query"])

        if result.get("status") == "success":
            for item in result.get("data", {}).get("result", []):
                ns = item.get("metric", {}).get("namespace")
                if not ns or ns not in summary_map:
                    continue

                try:
                    value = float(item.get("value", [None, "0"])[1])
                except (ValueError, TypeError):
                    value = 0.0

                summary_map[ns]["disk_iops"] = format_iops_per_sec(value)
                active_ns.add(ns)

        result = prom_repo.instant_series(nq.NAMESPACE_DISK_THROUGHPUT_RATE_5M["query"])

        if result.get("status") == "success":
            for item in result.get("data", {}).get("result", []):
                ns = item.get("metric", {}).get("namespace")
                if not ns or ns not in summary_map:
                    continue

                try:
                    value = float(item.get("value", [None, "0"])[1])
                except (ValueError, TypeError):
                    value = 0.0

                summary_map[ns]["disk_throughput"] = format_bytes_per_sec_iec(value)
                active_ns.add(ns)

        return [
            v for k, v in summary_map.items()
            if (
                k in active_ns
                or v.get("pods", 0) > 0
                or v.get("workloads", 0) > 0
                or v.get("services", 0) > 0
            )
        ]
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch namespace summary",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="CLUSTER_SUMMARY_BY_NAMESPACE_FETCH_FAILED",
        ) from exc

def cluster_events():
    try:
        events = k8s_repo.list_events()
        def is_cluster_event(ev):
            involved = getattr(ev, "involved_object", None)
            metadata = getattr(ev, "metadata", None)
            namespace = getattr(metadata, "namespace", None)
            return (
                (involved and involved.kind == "Node")
                or not namespace
                or namespace == "kube-system"
            )

        return build_event_summary(
            events,
            predicate=is_cluster_event,
            include_namespace=True,
            namespace_fallback="cluster",
        )
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch cluster events",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="CLUSTER_EVENTS_FETCH_FAILED",
        ) from exc
