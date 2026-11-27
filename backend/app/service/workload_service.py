from http import HTTPStatus
from app.repository import k8s_repo
from app.repository import prom_repo
from utils.parse_utils import format_bytes_iec, format_bytes_si
from utils.parse_utils import add_quantities, format_number
from utils.time_utils import format_relative_time
from utils.pod_utils import get_pod_info, build_pod_metric_map
from utils.event_utils import build_event_summary
from app.service.formatters.prom_chart import prom_range_to_chart
from app.query import workload_query as wq
from app.query import cluster_query as cq
from app.exceptions import ApiException

def _controller_owner(refs):
    if not refs:
        return None
    for r in refs:
        if getattr(r, "controller", None):
            return r
    return refs[0]

def namespace_list():
    try:
        namespaces = k8s_repo.list_active_namespaces()
        namespace_list = ["all"]

        namespace_list.extend(n.metadata.name for n in namespaces)

        return {"namespace_list": namespace_list}
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch workload namespace list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="WORKLOAD_NAMESPACE_LIST_FETCH_FAILED",
        ) from exc

def workload_status(namespace_name: str):
    try:
        ns = None if namespace_name == "all" else namespace_name

        dep = k8s_repo.list_deployments(ns)
        sts = k8s_repo.list_statefulsets(ns)
        dms = k8s_repo.list_daemonsets(ns)

        total_workloads = len(dep + sts + dms)

        total_pods = 0
        failed = 0
        degraded = 0

        for d in dep:
            desired = d.spec.replicas or 0
            ready = d.status.ready_replicas or 0 if d.status else 0

            total_pods += desired

            if desired > 0:
                if ready == 0:
                    failed += 1
                elif ready < desired:
                    degraded += 1

        for s in sts:
            desired = s.spec.replicas or 0
            ready = s.status.ready_replicas or 0 if s.status else 0

            total_pods += desired

            if desired > 0:
                if ready == 0:
                    failed += 1
                elif ready < desired:
                    degraded += 1

        for d in dms:
            desired = d.status.desired_number_scheduled or 0 if d.status else 0
            ready = d.status.number_ready or 0 if d.status else 0

            total_pods += desired

            if desired > 0:
                if ready == 0:
                    failed += 1
                elif ready < desired:
                    degraded += 1

        total_cpu = prom_repo.instant(cq.CLUSTER_CPU_TOTAL_CURRENT["query"]) or 0.0
        total_mem = prom_repo.instant(cq.CLUSTER_MEM_TOTAL_CURRENT["query"]) or 0.0
        used_cpu, used_mem = namespace_resource_usage(namespace_name)

        return {
            "total_workloads": total_workloads,
            "failed": failed,
            "degraded": degraded,
            "total_pods": total_pods,
            "cpu": f"{format_number(used_cpu)} / {format_number(total_cpu)} cores",
            "memory": f"{format_bytes_iec(used_mem)} / {format_bytes_iec(total_mem)}"
        }
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch workload status",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="WORKLOAD_STATUS_FETCH_FAILED",
        ) from exc

def namespace_resource_usage(namespace_name: str):
    if namespace_name == "all":
        cpu_query = wq.WORKLOAD_CPU_USAGE_ALL_5M["query"]
        memory_query = wq.WORKLOAD_MEMORY_USAGE_ALL_CURRENT["query"]
    else:
        cpu_query = wq.WORKLOAD_CPU_USAGE_BY_NAMESPACE_5M["query"].format(
            namespace=namespace_name
        )
        memory_query = wq.WORKLOAD_MEMORY_USAGE_BY_NAMESPACE_CURRENT["query"].format(
            namespace=namespace_name
        )

    cpu_used = prom_repo.instant(cpu_query) or 0.0
    memory_used = prom_repo.instant(memory_query) or 0.0

    return cpu_used, memory_used

def workload_list(namespace_name: str):
    try:
        ns = None if namespace_name == "all" else namespace_name

        dep = k8s_repo.list_deployments(ns)
        sts = k8s_repo.list_statefulsets(ns)
        dms = k8s_repo.list_daemonsets(ns)
        pods = k8s_repo.list_pods(ns)
        metrics = k8s_repo.list_pod_metrics(ns)

        dep_list = []
        sts_list = []
        dms_list = []

        for d in dep:

            name = d.metadata.name
            namespace = d.metadata.namespace

            desired = d.spec.replicas or 0
            ready = d.status.ready_replicas or 0 if d.status else 0

            replicas = f"{ready}/{desired}"

            if desired > 0:
                if ready == 0:
                    status = "Failed"
                elif ready < desired:
                    status = "Degraded"
                else:
                    status = "Healthy"
            else:
                status = "Healthy"

            age = format_relative_time(d.metadata.creation_timestamp)

            dep_list.append({
                "name": name,
                "namespace": namespace,
                "replicas": replicas,
                "status": status,
                "age": age,
                "restarts": 0,
                "cpu": 0,
                "memory": 0,
                "pods": []
            })

        for s in sts:
            name = s.metadata.name
            namespace = s.metadata.namespace

            desired = s.spec.replicas or 0
            ready = s.status.ready_replicas or 0 if s.status else 0

            replicas = f"{ready}/{desired}"

            if desired > 0:
                if ready == 0:
                    status = "Failed"
                elif ready < desired:
                    status = "Degraded"
                else:
                    status = "Healthy"
            else:
                status = "Healthy"

            age = format_relative_time(s.metadata.creation_timestamp)

            sts_list.append({
                "name": name,
                "namespace": namespace,
                "replicas": replicas,
                "status": status,
                "age": age,
                "restarts": 0,
                "cpu": 0,
                "memory": 0,
                "pods": []
            })

        for d in dms:
            name = d.metadata.name
            namespace = d.metadata.namespace

            desired = d.status.desired_number_scheduled or 0 if d.status else 0
            ready = d.status.number_ready or 0 if d.status else 0

            replicas = f"{ready}/{desired}"

            if desired > 0:
                if ready == 0:
                    status = "Failed"
                elif ready < desired:
                    status = "Degraded"
                else:
                    status = "Healthy"
            else:
                status = "Healthy"

            age = format_relative_time(d.metadata.creation_timestamp)

            dms_list.append({
                "name": name,
                "namespace": namespace,
                "replicas": replicas,
                "status": status,
                "age": age,
                "restarts": 0,
                "cpu": 0,
                "memory": 0,
                "pods": []
            })

        pod_metric_map = build_pod_metric_map(metrics)

        rs_list = k8s_repo.list_replica_sets(ns)
        rs_to_deployment = {}
        for rs in rs_list:
            rs_ns = rs.metadata.namespace
            dep_name = None
            for ref in rs.metadata.owner_references or []:
                if ref.kind == "Deployment" and getattr(ref, "controller", None):
                    dep_name = ref.name
                    break
            if dep_name is None:
                for ref in rs.metadata.owner_references or []:
                    if ref.kind == "Deployment":
                        dep_name = ref.name
                        break
            if dep_name is not None:
                rs_to_deployment[(rs_ns, rs.metadata.name)] = dep_name

        dep_by_key = {(d["namespace"], d["name"]): d for d in dep_list}
        sts_by_key = {(s["namespace"], s["name"]): s for s in sts_list}
        dms_by_key = {(dm["namespace"], dm["name"]): dm for dm in dms_list}

        for p in pods:
            if not p.metadata.owner_references:
                continue

            owner = _controller_owner(p.metadata.owner_references)
            if not owner:
                continue
            pod_ns = p.metadata.namespace

            restarts = sum(cs.restart_count for cs in (p.status.container_statuses or []))

            metric = pod_metric_map.get(
                (pod_ns, p.metadata.name), {}
            )
            cpu = metric.get("cpu")
            mem = metric.get("memory")

            row = None
            if owner.kind == "ReplicaSet":
                dep_name = rs_to_deployment.get((pod_ns, owner.name))
                if dep_name is None:
                    continue
                row = dep_by_key.get((pod_ns, dep_name))
            elif owner.kind == "StatefulSet":
                row = sts_by_key.get((pod_ns, owner.name))
            elif owner.kind == "DaemonSet":
                row = dms_by_key.get((pod_ns, owner.name))

            if not row:
                continue

            row["restarts"] += restarts
            row["pods"].append(p.metadata.name)
            row["cpu"] = add_quantities(row["cpu"], cpu)
            row["memory"] = add_quantities(row["memory"], mem)

        return {
            "deployment": dep_list,
            "statefulset": sts_list,
            "daemonset": dms_list
        }
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch workload list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="WORKLOAD_LIST_FETCH_FAILED",
        ) from exc

def cpu_usage(namespace_name: str, workload_type: str, workload_name: str, start_date: str, end_date: str):
    try:
        query = wq.WORKLOAD_CPU_USAGE_5M["query"].format(
            namespace=namespace_name,
            workload=workload_name,
            workload_type=workload_type
        )

        result = prom_repo.history_auto_step(query, start_date, end_date)

        return prom_range_to_chart(
            result,
            label_key="pod",
            default_name="unknown_pod",
            round_digits=5
        )
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch workload cpu usage",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="WORKLOAD_CPU_USAGE_FETCH_FAILED",
        ) from exc

def memory_usage(namespace_name: str, workload_type: str, workload_name: str, start_date: str, end_date: str):
    try:
        query = wq.WORKLOAD_MEM_USAGE_CURRENT["query"].format(
            namespace=namespace_name,
            workload=workload_name,
            workload_type=workload_type
        )

        result = prom_repo.history_auto_step(query, start_date, end_date)

        return prom_range_to_chart(
            result,
            label_key="pod",
            default_name="unknown_pod",
        )
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch workload memory usage",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="WORKLOAD_MEMORY_USAGE_FETCH_FAILED",
        ) from exc

def network_received(namespace_name: str, workload_type: str, workload_name: str, start_date: str, end_date: str):
    try:
        query = wq.WORKLOAD_NET_RECV_5M["query"].format(
            namespace=namespace_name,
            workload=workload_name,
            workload_type=workload_type
        )

        result = prom_repo.history_auto_step(query, start_date, end_date)

        return prom_range_to_chart(
            result,
            label_key="pod",
            default_name="unknown_pod",
        )
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch workload network received",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="WORKLOAD_NETWORK_RECEIVED_FETCH_FAILED",
        ) from exc

def network_transmitted(namespace_name: str, workload_type: str, workload_name: str, start_date: str, end_date: str):
    try:
        query = wq.WORKLOAD_NET_TRANS_5M["query"].format(
            namespace=namespace_name,
            workload=workload_name,
            workload_type=workload_type
        )

        result = prom_repo.history_auto_step(query, start_date, end_date)

        return prom_range_to_chart(
            result,
            label_key="pod",
            default_name="unknown_pod",
        )
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch workload network transmitted",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="WORKLOAD_NETWORK_TRANSMITTED_FETCH_FAILED",
        ) from exc

def pod_list(namespace_name: str, workload_name: str):
    try:
        metrics = k8s_repo.list_pod_metrics(namespace_name)

        pods, sidecar_lookup = k8s_repo.list_pods_with_sidecar_lookup(namespace_name)

        pod_metric_map = build_pod_metric_map(metrics)

        rs_list = k8s_repo.list_replica_sets(namespace_name)
        rs_to_deployment = {}
        for rs in rs_list:
            rs_ns = rs.metadata.namespace
            dep_name = None
            for ref in rs.metadata.owner_references or []:
                if ref.kind == "Deployment" and getattr(ref, "controller", None):
                    dep_name = ref.name
                    break
            if dep_name is None:
                for ref in rs.metadata.owner_references or []:
                    if ref.kind == "Deployment":
                        dep_name = ref.name
                        break
            if dep_name is not None:
                rs_to_deployment[(rs_ns, rs.metadata.name)] = dep_name

        pod_list = []
        for p in pods:

            if not p.metadata.owner_references:
                continue

            owner = _controller_owner(p.metadata.owner_references)
            if not owner:
                continue

            if owner.kind == "ReplicaSet":
                dep_name = rs_to_deployment.get((p.metadata.namespace, owner.name))
                if dep_name is None:
                    continue
                if workload_name != dep_name:
                    continue

            elif owner.kind == "StatefulSet":
                if workload_name != owner.name:
                    continue

            elif owner.kind == "DaemonSet":
                if workload_name != owner.name:
                    continue

            else:
                continue

            metric = pod_metric_map.get(
                (p.metadata.namespace, p.metadata.name), {}
            )
            cpu = metric.get("cpu")
            mem = metric.get("memory")

            sidecars = sidecar_lookup.get(p.metadata.uid, frozenset())
            pod_info = get_pod_info(p, sidecar_names=sidecars)

            status = pod_info["status"]

            ready_str = pod_info["ready"]

            restarts = pod_info["restarts"]

            age = format_relative_time(p.metadata.creation_timestamp)

            node = p.spec.node_name or "<none>"

            pod_list.append({
                "name": p.metadata.name,
                "status": status,
                "ready": ready_str,
                "restarts": restarts,
                "age": age,
                "node": node,
                "cpu": cpu,
                "memory": format_bytes_iec(mem) if mem is not None else None
            })

        return pod_list
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch workload pod list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="WORKLOAD_POD_LIST_FETCH_FAILED",
        ) from exc

def events(namespace_name: str, workload_name: str):
    try:
        pods = k8s_repo.list_pods(namespace_name)
        target_pods = set()
        rs_list = k8s_repo.list_replica_sets(namespace_name)
        rs_to_deployment = {}
        for rs in rs_list:
            rs_ns = rs.metadata.namespace
            dep_name = None
            for ref in rs.metadata.owner_references or []:
                if ref.kind == "Deployment" and getattr(ref, "controller", None):
                    dep_name = ref.name
                    break
            if dep_name is None:
                for ref in rs.metadata.owner_references or []:
                    if ref.kind == "Deployment":
                        dep_name = ref.name
                        break
            if dep_name is not None:
                rs_to_deployment[(rs_ns, rs.metadata.name)] = dep_name

        for p in pods:
            if not p.metadata.owner_references:
                continue

            owner = _controller_owner(p.metadata.owner_references)
            if not owner:
                continue

            matched = False
            if owner.kind == "ReplicaSet":
                dep_name = rs_to_deployment.get((p.metadata.namespace, owner.name))
                if dep_name is not None and workload_name == dep_name:
                    matched = True
            elif owner.kind == "StatefulSet":
                matched = workload_name == owner.name
            elif owner.kind == "DaemonSet":
                matched = workload_name == owner.name

            if matched:
                target_pods.add(p.metadata.name)

        raw = k8s_repo.list_events(namespace_name)

        def _workload_pod_event(ev):
            obj = getattr(ev, "involved_object", None)
            return bool(obj and obj.kind == "Pod" and obj.name in target_pods)

        predicate = _workload_pod_event if workload_name else None
        return build_event_summary(raw, predicate=predicate)
    except Exception as exc:
        raise ApiException(
            message="Failed to fetch workload events",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="WORKLOAD_EVENTS_FETCH_FAILED",
        ) from exc
