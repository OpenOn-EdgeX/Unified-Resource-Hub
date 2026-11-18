NODE_CPU_TOTAL_CURRENT = {
    "query": ('count(node_cpu_seconds_total{mode="system", instance="%s"})'),
    "desc": "해당 노드 CPU 총 코어 수 (count)",
}

NODE_CPU_USAGE_5M = {
    "query": (
        '100 - (avg(rate(node_cpu_seconds_total{mode="idle", instance="%s"}[5m])) * 100)'
    ),
    "desc": "해당 노드 CPU 사용률 (%, 5분 rate)",
}

NODE_CPU_USAGE_CORES_5M = {
    "query": (
        "sum("
        "rate(node_cpu_seconds_total{"
        'mode!="idle", '
        'mode!="iowait", '
        'instance="%s"'
        "}[5m])"
        ")"
    ),
    "desc": "해당 노드 전체 CPU 사용량 (cores, 5분 rate)",
}

NODE_CPU_USAGE_BY_POD_5M = {
    "query": (
        "sum by (pod) ("
        "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m{"
        'cluster="", '
        'node="%s"'
        "}"
        ")"
    ),
    "desc": "해당 노드 Pod별 CPU 사용량 (cores, 5분 rate, recording rule)",
}

NODE_LOAD_AVG_1M = {
    "query": ('node_load1{instance="%s"}'),
    "desc": "해당 노드 Load Average (1분)",
}

NODE_LOAD_AVG_5M = {
    "query": ('node_load5{instance="%s"}'),
    "desc": "해당 노드 Load Average (5분)",
}

NODE_LOAD_AVG_15M = {
    "query": ('node_load15{instance="%s"}'),
    "desc": "해당 노드 Load Average (15분)",
}

NODE_MEM_TOTAL_CURRENT = {
    "query": ('node_memory_MemTotal_bytes{instance="%s"}'),
    "desc": "해당 노드 메모리 총량 (bytes)",
}

NODE_MEM_USAGE_CURRENT = {
    "query": (
        '(1 - (node_memory_MemAvailable_bytes{instance="%s"} '
        '/ node_memory_MemTotal_bytes{instance="%s"})) * 100'
    ),
    "desc": "해당 노드 메모리 사용률 (%, 시점 기준)",
}

NODE_MEMORY_USAGE_BYTES_CURRENT = {
    "query": (
        'node_memory_MemTotal_bytes{instance="%s"} '
        '- node_memory_MemAvailable_bytes{instance="%s"}'
    ),
    "desc": "해당 노드 메모리 사용량 (bytes, 시점 기준)",
}

NODE_MEMORY_USAGE_BY_POD_CURRENT = {
    "query": (
        "sum by (pod) ("
        "container_memory_working_set_bytes{"
        'node="%s", '
        'container!="", '
        'pod!=""'
        "}"
        ")"
    ),
    "desc": "해당 노드 Pod별 메모리 사용량 (bytes, 시점 기준)",
}

NODE_MEM_USED_BYTES_CURRENT = {
    "query": (
        'node_memory_MemTotal_bytes{instance="%(instance)s"} '
        '- node_memory_MemFree_bytes{instance="%(instance)s"} '
        '- node_memory_Buffers_bytes{instance="%(instance)s"} '
        '- node_memory_Cached_bytes{instance="%(instance)s"}'
    ),
    "desc": "해당 노드 사용 메모리 (bytes, 시점 기준)",
}

NODE_MEM_BUFFERS_BYTES_CURRENT = {
    "query": ('node_memory_Buffers_bytes{instance="%s"}'),
    "desc": "해당 노드 메모리 버퍼 (bytes, 시점 기준)",
}

NODE_MEM_CACHED_BYTES_CURRENT = {
    "query": ('node_memory_Cached_bytes{instance="%s"}'),
    "desc": "해당 노드 메모리 캐시 (bytes, 시점 기준)",
}

NODE_MEM_FREE_BYTES_CURRENT = {
    "query": ('node_memory_MemFree_bytes{instance="%s"}'),
    "desc": "해당 노드 여유 메모리 (bytes, 시점 기준)",
}

NODE_DISK_TOTAL_CURRENT = {
    "query": (
        'sum(node_filesystem_size_bytes{instance="%s", '
        'fstype!~"tmpfs|overlay|squashfs|aufs"})'
    ),
    "desc": "해당 노드 디스크 총량 (bytes)",
}

NODE_DISK_USAGE_CURRENT = {
    "query": (
        "100 - ("
        'sum(node_filesystem_avail_bytes{instance="%s", '
        'fstype!~"tmpfs|overlay|squashfs|aufs"}) '
        "/ "
        'sum(node_filesystem_size_bytes{instance="%s", '
        'fstype!~"tmpfs|overlay|squashfs|aufs"}) * 100)'
    ),
    "desc": "해당 노드 디스크 사용률 (%, 시점 기준)",
}

NODE_DISK_READ_BYTES_5M = {
    "query": (
        "sum("
        "rate(node_disk_read_bytes_total{"
        'instance="%s", '
        'device=~"(mmcblk.p.+|nvme.+|rbd.+|sd.+|vd.+|xvd.+|dm-.+|md.+|dasd.+)"'
        "}[5m])"
        ")"
    ),
    "desc": "해당 노드 디스크 읽기 처리량 (bytes/s, 5분 rate)",
}

NODE_DISK_WRITE_BYTES_5M = {
    "query": (
        "sum("
        "rate(node_disk_written_bytes_total{"
        'instance="%s", '
        'device=~"(mmcblk.p.+|nvme.+|rbd.+|sd.+|vd.+|xvd.+|dm-.+|md.+|dasd.+)"'
        "}[5m])"
        ")"
    ),
    "desc": "해당 노드 디스크 쓰기 처리량 (bytes/s, 5분 rate)",
}

NODE_DISK_IO_TIME_5M = {
    "query": (
        "avg("
        "rate(node_disk_io_time_seconds_total{"
        'instance="%s", '
        'device=~"(mmcblk.p.+|nvme.+|rbd.+|sd.+|vd.+|xvd.+|dm-.+|md.+|dasd.+)"'
        "}[5m])"
        ") * 100"
    ),
    "desc": "해당 노드 디스크 I/O busy 비율 (%, 5분 rate)",
}

NODE_DISK_SPACE_SIZE_BY_MOUNT_CURRENT = {
    "query": (
        "max by (mountpoint) ("
        'node_filesystem_size_bytes{instance="%s", fstype!="", mountpoint!=""}'
        ")"
    ),
    "desc": "해당 노드 마운트포인트별 디스크 총량 (bytes, 시점 기준)",
}

NODE_DISK_SPACE_AVAIL_BY_MOUNT_CURRENT = {
    "query": (
        "max by (mountpoint) ("
        'node_filesystem_avail_bytes{instance="%s", fstype!="", mountpoint!=""}'
        ")"
    ),
    "desc": "해당 노드 마운트포인트별 디스크 여유량 (bytes, 시점 기준)",
}

NODE_NETWORK_RECEIVE_BYTES_BY_DEVICE_5M = {
    "query": (
        "rate(node_network_receive_bytes_total{"
        'instance="%s", '
        'device!="lo"'
        "}[5m])"
    ),
    "desc": "해당 노드 네트워크 수신 트래픽 (bytes/s, 5분 rate, device별)",
}

NODE_NETWORK_TRANSMIT_BYTES_BY_DEVICE_5M = {
    "query": (
        "rate(node_network_transmit_bytes_total{"
        'instance="%s", '
        'device!="lo"'
        "}[5m])"
    ),
    "desc": "해당 노드 네트워크 송신 트래픽 (bytes/s, 5분 rate, device별)",
}
