NAMESPACE_CPU_USAGE_5M = {
    "query": (
        'sum(node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m{cluster=""}) '
        'by (namespace)'
    ),
    "desc": "Namespace별 CPU 사용량 (cores, 5분 rate)"
}

NAMESPACE_MEMORY_USAGE_CURRENT = {
    "query": (
        'sum(container_memory_rss{job="kubelet", metrics_path="/metrics/cadvisor", '
        'cluster="", container!=""}) by (namespace)'
    ),
    "desc": "Namespace별 Memory 사용량 (bytes, RSS 스냅샷 시점)"
}

NAMESPACE_NETWORK_RX_RATE_5M = {
    "query": (
        'sum(rate(container_network_receive_bytes_total{job="kubelet", '
        'metrics_path="/metrics/cadvisor", cluster="", namespace=~".+"}[5m])) '
        'by (namespace)'
    ),
    "desc": "Namespace별 네트워크 수신 속도 (bytes/s, 5분 rate)"
}

NAMESPACE_NETWORK_TX_RATE_5M = {
    "query": (
        'sum(rate(container_network_transmit_bytes_total{job="kubelet", '
        'metrics_path="/metrics/cadvisor", cluster="", namespace=~".+"}[5m])) '
        'by (namespace)'
    ),
    "desc": "Namespace별 네트워크 송신 속도 (bytes/s, 5분 rate)"
}

NAMESPACE_DISK_IOPS_RATE_5M = {
    "query": (
        'sum by(namespace) ('
        'rate(container_fs_reads_total{job="kubelet", metrics_path="/metrics/cadvisor", '
        'container!="", device=~"(/dev/)?(mmcblk.p.+|nvme.+|rbd.+|sd.+|vd.+|xvd.+|dm-.+|md.+|dasd.+)", '
        'cluster="", namespace!=""}[5m]) + '
        'rate(container_fs_writes_total{job="kubelet", metrics_path="/metrics/cadvisor", '
        'container!="", device=~"(/dev/)?(mmcblk.p.+|nvme.+|rbd.+|sd.+|vd.+|xvd.+|dm-.+|md.+|dasd.+)", '
        'cluster="", namespace!=""}[5m])'
        ')'
    ),
    "desc": "Namespace별 Disk IOPS (io/s, 5분 rate)"
}

NAMESPACE_DISK_THROUGHPUT_RATE_5M = {
    "query": (
        'sum by(namespace) ('
        'rate(container_fs_reads_bytes_total{job="kubelet", metrics_path="/metrics/cadvisor", '
        'container!="", device=~"(/dev/)?(mmcblk.p.+|nvme.+|rbd.+|sd.+|vd.+|xvd.+|dm-.+|md.+|dasd.+)", '
        'cluster="", namespace!=""}[5m]) + '
        'rate(container_fs_writes_bytes_total{job="kubelet", metrics_path="/metrics/cadvisor", '
        'container!="", device=~"(/dev/)?(mmcblk.p.+|nvme.+|rbd.+|sd.+|vd.+|xvd.+|dm-.+|md.+|dasd.+)", '
        'cluster="", namespace!=""}[5m])'
        ')'
    ),
    "desc": "Namespace별 Disk Throughput (bytes/s, 5분 rate)"
}
