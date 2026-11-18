from http import HTTPStatus
from app.repository import k8s_repo
from app.repository import prom_repo
from app.repository.prom_repo import instant, instant_series, history
from utils.parse_utils import format_bytes_iec, format_bytes_si
from utils.time_utils import format_relative_time, KST
from utils.pod_utils import get_pod_info, build_pod_metric_map
from app.service.formatters.prom_chart import prom_range_to_chart
from app.query import node_query as nq
from app.query import gpu_query as gq
from app.exceptions import ApiException

def node_list():
    try:
        nodes = k8s_repo.list_nodes()
        node_list = [n.metadata.name for n in nodes]

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_LIST_FETCH_FAILED",
        ) from exc

    return {"node_list": node_list}

def node_info(node_name: str):
    try:
        node = k8s_repo.get_node(node_name)
        info = node.status.node_info

        labels = node.metadata.labels or {}

        if (
            "node-role.kubernetes.io/control-plane" in labels
            or "node-role.kubernetes.io/master" in labels
        ):
            role = "master"
        else:
            role = "worker"

        uptime = "-"
        ready_condition = next(
            (c for c in node.status.conditions or [] if c.type == "Ready"),
            None,
        )

        if ready_condition is None:
            ready_status = "Unknown"
        else:
            ready_status = "Ready" if ready_condition.status == "True" else "NotReady"

            dt = ready_condition.last_transition_time
            if dt:
                uptime = (
                    dt
                    .astimezone(KST)
                    .strftime("%Y-%m-%d %H:%M:%S")
                )

        allocatable = node.status.allocatable or {}
        is_gpu = "nvidia.com/gpu" in allocatable

        return {
            "node": node.metadata.name,
            "role": role,
            "status": ready_status,
            "os": info.os_image,
            "kubelet_version": info.kubelet_version,
            "container_runtime": info.container_runtime_version,
            "uptime": uptime,
            "is_gpu": is_gpu,
        }
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node info",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_INFO_FETCH_FAILED",
        ) from exc

def performance_summary(node_name: str):
    try:
        cpu_total = instant(nq.NODE_CPU_TOTAL_CURRENT["query"] % node_name) or 0
        cpu_usage = instant(nq.NODE_CPU_USAGE_5M["query"] % node_name) or 0

        mem_total = instant(nq.NODE_MEM_TOTAL_CURRENT["query"] % node_name) or 0
        mem_usage = (
            instant(nq.NODE_MEM_USAGE_CURRENT["query"] % (node_name, node_name)) or 0
        )

        disk_total = instant(nq.NODE_DISK_TOTAL_CURRENT["query"] % node_name) or 0
        disk_usage = (
            instant(nq.NODE_DISK_USAGE_CURRENT["query"] % (node_name, node_name)) or 0
        )

        return {
            "node": node_name,
            "cpu": {
                "total_cores": f"{int(cpu_total)} cores",
                "usage_percent": round(cpu_usage, 2),
            },
            "memory": {
                "total_gb": format_bytes_si(mem_total, precision=0),
                "usage_percent": round(mem_usage, 2),
            },
            "disk": {
                "total_gb": format_bytes_si(disk_total, precision=0),
                "usage_percent": round(disk_usage, 2),
            }
        }
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node performance summary",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_PERFORMANCE_SUMMARY_FETCH_FAILED",
        ) from exc

def load_average(node_name: str, start_date: str, end_date: str):
    try:
        queries = {
            "1m load average": nq.NODE_LOAD_AVG_1M["query"] % node_name,
            "5m load average": nq.NODE_LOAD_AVG_5M["query"] % node_name,
            "15m load average": nq.NODE_LOAD_AVG_15M["query"] % node_name,
        }

        merged_result = []

        for name, query in queries.items():
            result = prom_repo.history_auto_step(query, start_date, end_date)

            for item in result or []:
                metric = item.setdefault("metric", {})
                metric["series"] = name

            merged_result.extend(result or [])

        return prom_range_to_chart(
            merged_result,
            label_key="series",
            default_name="value",
            round_digits=2
        )
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node load average",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_LOAD_AVERAGE_FETCH_FAILED",
        ) from exc

def gpu_summary(node_name: str):
    try:
        util_series = instant_series(gq.GPU_UTIL_METRIC["query"] % node_name)["data"]["result"]
        mem_used_series = instant_series(gq.GPU_FB_USED_METRIC["query"] % node_name)["data"]["result"]
        mem_free_series = instant_series(gq.GPU_FB_FREE_METRIC["query"] % node_name)["data"]["result"]
        temp_series = instant_series(gq.GPU_TEMP_METRIC["query"] % node_name)["data"]["result"]

        gpu_map = {}

        def ensure_gpu(gpu, model_name=None):
            if gpu not in gpu_map:
                gpu_map[gpu] = {
                    "gpu": int(gpu),
                    "modelName": model_name or "-",
                    "gpu_usage_percent": 0.0,
                    "memory_usage_percent": 0.0,
                    "temperature": 0.0,
                    "pstate": "P-",
                    "allocated_pod": 0,
                }
            else:
                if model_name and gpu_map[gpu]["modelName"] == "-":
                    gpu_map[gpu]["modelName"] = model_name
            return gpu_map[gpu]

        for item in util_series:
            if item["metric"].get("Hostname") != node_name:
                continue
            gpu = item["metric"].get("gpu")
            model_name = item["metric"].get("modelName")

            ensure_gpu(gpu, model_name)["gpu_usage_percent"] = round(
                float(item["value"][1]), 2
            )

        mem_used_map = {}
        for item in mem_used_series:
            if item["metric"].get("Hostname") != node_name:
                continue
            mem_used_map[item["metric"].get("gpu")] = float(item["value"][1])

        mem_free_map = {}
        for item in mem_free_series:
            if item["metric"].get("Hostname") != node_name:
                continue
            mem_free_map[item["metric"].get("gpu")] = float(item["value"][1])

        for gpu, used in mem_used_map.items():
            free = mem_free_map.get(gpu)
            if free is None:
                continue
            total = used + free
            if total > 0:
                ensure_gpu(gpu)["memory_usage_percent"] = round(
                    (used / total) * 100, 2
                )

        for item in temp_series:
            if item["metric"].get("Hostname") != node_name:
                continue
            gpu = item["metric"].get("gpu")
            temp = float(item["value"][1])
            ensure_gpu(gpu)["temperature"] = round(temp, 1) if temp > 0 else 0.0

        temp_history = history(gq.GPU_TEMP_METRIC["query"] % node_name)
        for info in gpu_map.values():
            info["temperature_history"] = temp_history

        pstate_series = instant_series(gq.GPU_PSTATE_METRIC['query'] % node_name)
        for item in (pstate_series.get('data') or {}).get('result', []):
            gpu = item.get('metric', {}).get('gpu')
            value = item.get('value') or []
            if gpu in gpu_map and len(value) == 2:
                try:
                    state = int(float(value[1]))
                except (ValueError, TypeError, OverflowError):
                    continue
                if 0 <= state <= 15:
                    gpu_map[gpu]['pstate'] = f'P{state}'

        allocated_pod = count_gpu_pods_on_node(node_name)
        for info in gpu_map.values():
            info["allocated_pod"] = allocated_pod

        return list(gpu_map.values())
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node gpu summary",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_GPU_SUMMARY_FETCH_FAILED",
        ) from exc

def count_gpu_pods_on_node(node_name: str) -> int:
    count = 0
    for pod in k8s_repo.list_pods():
        if pod.spec.node_name != node_name:
            continue
        if pod.status.phase != "Running":
            continue

        selectors = pod.spec.node_selector or {}
        if selectors.get("kubernetes.io/gpu") == "nvidia":
            count += 1

    return count

def cpu_usage(node_name: str, start_date: str, end_date: str):
    try:
        query = nq.NODE_CPU_USAGE_CORES_5M["query"] % node_name
        result = prom_repo.history_auto_step(query, start_date, end_date)
        return prom_range_to_chart(result, round_digits=5)
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node cpu usage",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_CPU_USAGE_FETCH_FAILED",
        ) from exc

def cpu_usage_by_pod(node_name: str, start_date: str, end_date: str):
    try:
        query = nq.NODE_CPU_USAGE_BY_POD_5M["query"] % node_name
        result = prom_repo.history_auto_step(query, start_date, end_date)

        return prom_range_to_chart(
            result,
            label_key="pod",
            default_name="unknown_pod",
            round_digits=5
        )
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node cpu usage by pod",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_CPU_USAGE_BY_POD_FETCH_FAILED",
        ) from exc

def memory_usage(node_name: str, start_date: str, end_date: str):
    try:
        queries = {
            "memory used": nq.NODE_MEM_USED_BYTES_CURRENT["query"] % {"instance": node_name},
            "memory buffers": nq.NODE_MEM_BUFFERS_BYTES_CURRENT["query"] % node_name,
            "memory cached": nq.NODE_MEM_CACHED_BYTES_CURRENT["query"] % node_name,
            "memory free": nq.NODE_MEM_FREE_BYTES_CURRENT["query"] % node_name,
        }

        merged_result = []

        for name, query in queries.items():
            result = prom_repo.history_auto_step(query, start_date, end_date)

            for item in result or []:
                metric = item.setdefault("metric", {})
                metric["series"] = name

            merged_result.extend(result or [])

        return prom_range_to_chart(
            merged_result,
            label_key="series",
            default_name="memory",
        )
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node memory usage",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_MEMORY_USAGE_FETCH_FAILED",
        ) from exc

def memory_usage_by_pod(node_name: str, start_date: str, end_date: str):
    try:
        query = nq.NODE_MEMORY_USAGE_BY_POD_CURRENT["query"] % node_name
        result = prom_repo.history_auto_step(query, start_date, end_date)

        return prom_range_to_chart(
            result,
            label_key="pod",
            default_name="unknown_pod",
        )
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node memory usage by pod",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_MEMORY_USAGE_BY_POD_FETCH_FAILED",
        ) from exc

def disk_io(node_name: str, start_date: str, end_date: str):
    try:
        queries = {
            "disk read": nq.NODE_DISK_READ_BYTES_5M["query"] % node_name,
            "disk write": nq.NODE_DISK_WRITE_BYTES_5M["query"] % node_name,
            "disk io time": nq.NODE_DISK_IO_TIME_5M["query"] % node_name,
        }

        merged_result = []

        for name, query in queries.items():
            result = prom_repo.history_auto_step(query, start_date, end_date)

            for item in result or []:
                metric = item.setdefault("metric", {})
                metric["series"] = name

                values = item.get("values", [])
                if not values:
                    continue

                if name in ("disk read", "disk write"):
                    digits = 0
                else:
                    digits = 3

                item["values"] = [
                    [ts, round(float(val), digits)]
                    for ts, val in values
                ]

            merged_result.extend(result or [])

        return prom_range_to_chart(
            merged_result,
            label_key="series",
            default_name="disk",
        )
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node disk io",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_DISK_IO_FETCH_FAILED",
        ) from exc

def network_received(node_name: str, start_date: str, end_date: str):
    try:
        query = nq.NODE_NETWORK_RECEIVE_BYTES_BY_DEVICE_5M["query"] % node_name
        result = prom_repo.history_auto_step(query, start_date, end_date)

        return prom_range_to_chart(
            result,
            label_key="device",
            default_name="unknown_if",
        )
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node network received",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_NETWORK_RECEIVED_FETCH_FAILED",
        ) from exc

def network_transmitted(node_name: str, start_date: str, end_date: str):
    try:
        query = nq.NODE_NETWORK_TRANSMIT_BYTES_BY_DEVICE_5M["query"] % node_name
        result = prom_repo.history_auto_step(query, start_date, end_date)

        return prom_range_to_chart(
            result,
            label_key="device",
            default_name="unknown_if",
        )
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node network transmitted",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_NETWORK_TRANSMITTED_FETCH_FAILED",
        ) from exc

def disk_space_usage(node_name: str):
    try:
        size_query = nq.NODE_DISK_SPACE_SIZE_BY_MOUNT_CURRENT["query"] % node_name
        avail_query = nq.NODE_DISK_SPACE_AVAIL_BY_MOUNT_CURRENT["query"] % node_name

        size_resp = instant_series(size_query)
        avail_resp = instant_series(avail_query)

        size_result = size_resp.get("data", {}).get("result", [])
        avail_result = avail_resp.get("data", {}).get("result", [])

        size_map = {
            item["metric"]["mountpoint"]: float(item["value"][1])
            for item in size_result
            if "metric" in item and "mountpoint" in item["metric"]
        }

        avail_map = {
            item["metric"]["mountpoint"]: float(item["value"][1])
            for item in avail_result
            if "metric" in item and "mountpoint" in item["metric"]
        }

        table = []

        for mountpoint, size in size_map.items():
            avail = avail_map.get(mountpoint, 0.0)
            used = max(size - avail, 0.0)
            used_pct = (used / size * 100) if size > 0 else 0

            table.append({
                "mountpoint": mountpoint,
                "size_bytes": format_bytes_si(size),
                "avail_bytes": format_bytes_si(avail),
                "used_bytes": format_bytes_si(used),
                "used_percent": round(used_pct, 2),
            })

        return table
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch node disk space usage",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_DISK_SPACE_USAGE_FETCH_FAILED",
        ) from exc

def running_pods(node_name: str):
    try:

        pods, sidecar_lookup = k8s_repo.list_pods_by_node_with_sidecar_lookup(node_name)

        pod_metrics = k8s_repo.list_pod_metrics()
        metrics_map = build_pod_metric_map(pod_metrics)

        result = []

        for pod in pods:
            ns = pod.metadata.namespace
            name = pod.metadata.name

            sidecars = sidecar_lookup.get(pod.metadata.uid, frozenset())
            pod_info = get_pod_info(pod, sidecar_names=sidecars)

            status = pod_info["status"]

            ready_str = pod_info["ready"]

            restarts = pod_info["restarts"]

            age = format_relative_time(pod.metadata.creation_timestamp)

            metric = metrics_map.get((ns, name), {"cpu": 0.0, "memory": 0.0})
            cpu_usage = metric["cpu"]
            mem_usage = metric["memory"]

            result.append({
                "pod_name": name,
                "namespace": ns,
                "cpu_usage": round(cpu_usage, 3),
                "memory_usage": format_bytes_iec(mem_usage),
                "ready": ready_str,
                "status": status,
                "restarts": restarts,
                "age": age,
            })

        return result
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch running pods on node",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="NODE_RUNNING_PODS_FETCH_FAILED",
        ) from exc
