NODE_READY_COUNT = {
    "query": 'sum(kube_node_status_condition{condition="Ready",status="true"})',
    "desc": "Ready 상태의 노드 수 (count)"
}

NAMESPACE_ACTIVE_COUNT = {
    "query": 'sum(kube_namespace_status_phase{phase="Active"})',
    "desc": "Active 네임스페이스 수 (count)"
}

POD_RUNNING_COUNT = {
    "query": 'sum(kube_pod_status_phase{phase="Running"})',
    "desc": "Running 파드 수 (count)"
}

WORKLOAD_READY_COUNT = {
    "query": (
        "("
        "(count(kube_deployment_status_replicas_available == kube_deployment_spec_replicas) or vector(0)) + "
        "(count(kube_statefulset_status_replicas_ready == kube_statefulset_replicas) or vector(0)) + "
        "(count(kube_daemonset_status_number_ready == kube_daemonset_status_desired_number_scheduled) or vector(0))"
        ")"
    ),
    "desc": "Ready 상태 워크로드 수 (count)"
}

SERVICE_COUNT = {
    "query": (
        'count('
        '('
        'sum by (namespace, endpoint) (kube_endpoint_address{ready="true"}) > 0'
        ') unless on (namespace, endpoint) ('
        'sum by (namespace, endpoint) (kube_endpoint_address{ready!="true"}) > 0'
        ') and on (namespace, endpoint) ('
        'label_replace(kube_service_spec_type{type=~"ClusterIP|NodePort|LoadBalancer"} == 1, '
        '"endpoint", "$1", "service", "(.*)")'
        ')'
        ')'
    ),
    "desc": "정상 Endpoint만 가진 Service 수 (count, 대상 타입: ClusterIP|NodePort|LoadBalancer)",
}

CLUSTER_CPU_USAGE_5M = {
    "query": 'cluster:node_cpu:ratio_rate5m',
    "desc": "클러스터 CPU 사용률 (ratio, 5분 rate)"
}

CLUSTER_CPU_TOTAL_CURRENT = {
    "query": 'count(node_cpu_seconds_total{mode="system"})',
    "desc": "클러스터 CPU 총량 (cores, 노드 exporter 스냅샷 시점)"
}

CLUSTER_MEM_USAGE_CURRENT = {
    "query": (
        '1 - sum(:node_memory_MemAvailable_bytes:sum) '
        '/ sum(node_memory_MemTotal_bytes{job="node-exporter"})'
    ),
    "desc": "클러스터 Memory 사용률 (ratio, MemAvail/Total 스냅샷 시점)"
}

CLUSTER_MEM_TOTAL_CURRENT = {
    "query": 'sum(node_memory_MemTotal_bytes{job="node-exporter"})',
    "desc": "클러스터 Memory 총량 (bytes, 노드 exporter 스냅샷 시점)"
}

CLUSTER_DISK_USAGE_CURRENT = {
    "query": '''
        1 - (
          sum(node_filesystem_avail_bytes{fstype!~"tmpfs|overlay|squashfs|aufs"})
          /
          sum(node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs|aufs"})
        )
    ''',
    "desc": "클러스터 Disk 사용률 (ratio, 파일시스템 avail/size 스냅샷 시점)"
}

CLUSTER_DISK_TOTAL_CURRENT = {
    "query": (
        'sum(node_filesystem_size_bytes{fstype!~"tmpfs|overlay|squashfs|aufs"})'
    ),
    "desc": "클러스터 Disk 총량 (bytes, 파일시스템 size 스냅샷 시점)"
}

CLUSTER_DISK_READ_5M = {
    "query": (
        'round(sum('
        'rate(node_disk_read_bytes_total{device!~"^(loop.*|ram.*|dm-.*|sr0|fd.*|zram.*)$"}[5m])'
        ') / 1024)'
    ),
    "desc": "클러스터 디스크 읽기 속도 (KiB/s, 5분 rate)"
}

CLUSTER_DISK_WRITE_5M = {
    "query": (
        'round(sum('
        'rate(node_disk_written_bytes_total{device!~"^(loop.*|ram.*|dm-.*|sr0|fd.*|zram.*)$"}[5m])'
        ') / 1024)'
    ),
    "desc": "클러스터 디스크 쓰기 속도 (KiB/s, 5분 rate)"
}

CLUSTER_NET_RECV_5M = {
    "query": (
        'round(sum('
        'rate(node_network_receive_bytes_total{device!="lo"}[5m])'
        ') / 1024)'
    ),
    "desc": "클러스터 네트워크 수신량 (KiB/s, 5분 rate)"
}

CLUSTER_NET_TRANS_5M = {
    "query": (
        'round(sum('
        'rate(node_network_transmit_bytes_total{device!="lo"}[5m])'
        ') / 1024)'
    ),
    "desc": "클러스터 네트워크 송신량 (KiB/s, 5분 rate)"
}
