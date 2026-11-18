WORKLOAD_CPU_USAGE_5M = {
    "query": (
        'sum('
        'node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m'
        '{{cluster="", namespace="{namespace}"}} '
        '* on(namespace,pod) '
        'group_left(workload, workload_type) '
        'namespace_workload_pod:kube_pod_owner:relabel'
        '{{cluster="", namespace="{namespace}", workload="{workload}", workload_type="{workload_type}"}}'
        ') by (pod)'
    ),
    "desc": "Workload별 Pod CPU 사용량 (cores, 5분 rate)"
}

WORKLOAD_MEM_USAGE_CURRENT = {
    "query": (
        'sum('
        'container_memory_working_set_bytes{{cluster="", namespace="{namespace}", container!="", image!=""}} '
        '* on(namespace,pod) '
        'group_left(workload, workload_type) '
        'namespace_workload_pod:kube_pod_owner:relabel'
        '{{cluster="", namespace="{namespace}", workload="{workload}", workload_type="{workload_type}"}}'
        ') by (pod)'
    ),
    "desc": "Workload별 Pod Memory 사용량 (bytes, working set 스냅샷 시점)"
}

WORKLOAD_NET_RECV_5M = {
    "query": (
        'sum('
        'rate(container_network_receive_bytes_total'
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", namespace="{namespace}"}}[5m]) '
        '* on(namespace,pod) '
        'group_left(workload, workload_type) '
        'namespace_workload_pod:kube_pod_owner:relabel'
        '{{cluster="", namespace="{namespace}", workload="{workload}", workload_type="{workload_type}"}}'
        ') by (pod)'
    ),
    "desc": "Workload별 Pod 네트워크 수신량 (bytes/s, 5분 rate)"
}

WORKLOAD_NET_TRANS_5M = {
    "query": (
        'sum('
        'rate(container_network_transmit_bytes_total'
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", namespace="{namespace}"}}[5m]) '
        '* on(namespace,pod) '
        'group_left(workload, workload_type) '
        'namespace_workload_pod:kube_pod_owner:relabel'
        '{{cluster="", namespace="{namespace}", workload="{workload}", workload_type="{workload_type}"}}'
        ') by (pod)'
    ),
    "desc": "Workload별 Pod 네트워크 송신량 (bytes/s, 5분 rate)"
}

WORKLOAD_CPU_USAGE_ALL_5M = {
    "query": (
        'sum('
        'node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m'
        '{cluster=""} '
        '* on(namespace,pod) '
        'group_left(workload, workload_type) '
        'namespace_workload_pod:kube_pod_owner:relabel'
        '{cluster="", workload_type=~"deployment|statefulset|daemonset"}'
        ')'
    ),
    "desc": "전체 클러스터 Workload CPU 사용량 (cores, 5분 rate; 모든 Namespace 합산)"
}

WORKLOAD_MEMORY_USAGE_ALL_CURRENT = {
    "query": (
        'sum('
        'container_memory_working_set_bytes{cluster="", container!="", image!=""} '
        '* on(namespace,pod) '
        'group_left(workload, workload_type) '
        'namespace_workload_pod:kube_pod_owner:relabel'
        '{cluster="", workload_type=~"deployment|statefulset|daemonset"}'
        ')'
    ),
    "desc": "전체 클러스터 Workload Memory 사용량 (bytes, working set 스냅샷 시점; 모든 Namespace 합산)"
}

WORKLOAD_CPU_USAGE_BY_NAMESPACE_5M = {
    "query": (
        'sum('
        'node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m'
        '{{cluster="", namespace="{namespace}"}} '
        '* on(namespace,pod) '
        'group_left(workload, workload_type) '
        'namespace_workload_pod:kube_pod_owner:relabel'
        '{{cluster="", namespace="{namespace}", workload_type=~"deployment|statefulset|daemonset"}}'
        ')'
    ),
    "desc": "특정 Namespace Workload CPU 사용량 (cores, 5분 rate)"
}

WORKLOAD_MEMORY_USAGE_BY_NAMESPACE_CURRENT = {
    "query": (
        'sum('
        'container_memory_working_set_bytes{{cluster="", namespace="{namespace}", container!="", image!=""}} '
        '* on(namespace,pod) '
        'group_left(workload, workload_type) '
        'namespace_workload_pod:kube_pod_owner:relabel'
        '{{cluster="", namespace="{namespace}", workload_type=~"deployment|statefulset|daemonset"}}'
        ')'
    ),
    "desc": "특정 Namespace Workload Memory 사용량 (bytes, working set 스냅샷 시점)"
}
