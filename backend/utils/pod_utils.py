from utils.parse_utils import quantity_total

DEFAULT_POD_INFO = {
    "status": "Unknown",
    "ready": "-/-",
    "restarts": 0,
    "last_restart_at": None,
}

def _is_pod_initialized_condition_true(status):
    for cond in status.conditions or []:
        if cond.type == "Initialized":
            return cond.status == "True"
    return False

def _has_pod_ready_condition(status):
    for cond in status.conditions or []:
        if cond.type == "Ready" and cond.status == "True":
            return True
    return False

def get_pod_info(pod, sidecar_names=None):
    if not pod or not pod.status:
        return DEFAULT_POD_INFO

    sidecar_names = sidecar_names or frozenset()

    spec = pod.spec
    status = pod.status

    init_statuses = status.init_container_statuses or []
    container_statuses = status.container_statuses or []

    total = len(spec.containers or [])
    ready = 0
    restarts = 0
    restartable_init_restarts = 0
    last_restart_at = None
    last_restartable_init_restart_at = None

    reason = status.reason or status.phase or "Unknown"

    for cond in status.conditions or []:
        if cond.type == "PodScheduled" and cond.reason == "SchedulingGated":
            reason = "SchedulingGated"

    total += len(sidecar_names)

    initializing = False
    for i, cs in enumerate(init_statuses):
        restarts += cs.restart_count or 0

        if (
            cs.last_state
            and cs.last_state.terminated
            and cs.last_state.terminated.finished_at
        ):
            t = cs.last_state.terminated.finished_at
            if last_restart_at is None or t > last_restart_at:
                last_restart_at = t

        is_sidecar = cs.name in sidecar_names
        if is_sidecar:
            restartable_init_restarts += cs.restart_count or 0

            if (
                cs.last_state
                and cs.last_state.terminated
                and cs.last_state.terminated.finished_at
            ):
                t = cs.last_state.terminated.finished_at
                if (
                    last_restartable_init_restart_at is None
                    or t > last_restartable_init_restart_at
                ):
                    last_restartable_init_restart_at = t

        st = cs.state

        if st.terminated and st.terminated.exit_code == 0:
            continue

        if is_sidecar and cs.started:
            if cs.ready:
                ready += 1
            continue

        if st.terminated:
            t = st.terminated
            if not t.reason:
                if t.signal:
                    reason = f"Init:Signal:{t.signal}"
                else:
                    reason = f"Init:ExitCode:{t.exit_code}"
            else:
                reason = f"Init:{t.reason}"
            initializing = True
        elif (
            st.waiting and st.waiting.reason and st.waiting.reason != "PodInitializing"
        ):
            reason = f"Init:{st.waiting.reason}"
            initializing = True
        else:
            init_count = len(spec.init_containers or [])
            reason = f"Init:{i}/{init_count}"
            initializing = True
        break

    if (not initializing) or _is_pod_initialized_condition_true(status):

        restarts = restartable_init_restarts
        last_restart_at = last_restartable_init_restart_at
        has_running = False
        error_reason = ""

        for cs in reversed(container_statuses):
            restarts += cs.restart_count or 0
            if (
                cs.last_state
                and cs.last_state.terminated
                and cs.last_state.terminated.finished_at
            ):
                t = cs.last_state.terminated.finished_at
                if last_restart_at is None or t > last_restart_at:
                    last_restart_at = t
            st = cs.state

            if st.waiting and st.waiting.reason:
                reason = st.waiting.reason

            elif st.terminated:
                t = st.terminated
                if t.reason:
                    reason = t.reason
                elif t.signal:
                    reason = f"Signal:{t.signal}"
                else:
                    reason = f"ExitCode:{t.exit_code}"

                if t.exit_code != 0:
                    error_reason = reason

            elif cs.ready and st.running:
                has_running = True
                ready += 1

        if reason == "Completed":
            if has_running and _has_pod_ready_condition(status):
                reason = "Running"
            elif error_reason:
                reason = error_reason
            elif has_running:
                reason = "NotReady"

    if pod.metadata.deletion_timestamp:
        if status.reason == "NodeLost":
            reason = "Unknown"
        elif status.phase not in ("Succeeded", "Failed"):
            reason = "Terminating"

    return {
        "status": reason,
        "ready": f"{ready}/{total}",
        "restarts": restarts,
        "last_restart_at": last_restart_at,
    }

def build_pod_metric_map(metrics):
    pod_metric_map = {}

    for m in metrics or []:
        md = m.get("metadata", {})
        pod_key = (md.get("namespace") or "", md.get("name") or "")

        containers = m.get("containers") or []
        pod_metric_map[pod_key] = {
            resource: quantity_total(resource, ((c.get("usage") or {}).get(resource) for c in containers))
            if containers else None
            for resource in ("cpu", "memory")
        }

    return pod_metric_map
