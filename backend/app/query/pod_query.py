POD_TOTAL_CPU_USAGE_ALL_5M = {
    "query": (
        "sum("
        "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m"
        '{{cluster=""}}'
        ")"
    ),
    "desc": "전체 클러스터 Pod CPU 사용량 (cores, 5분 rate)",
}

POD_TOTAL_CPU_USAGE_BY_NS_5M = {
    "query": (
        "sum("
        "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m"
        '{{cluster="", namespace="{namespace}"}}'
        ")"
    ),
    "desc": "Namespace별 Pod CPU 사용량 (cores, 5분 rate)",
}

POD_TOTAL_CPU_USAGE_BY_NODE_5M = {
    "query": (
        "sum("
        "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m"
        '{{cluster="", node="{node}"}}'
        ")"
    ),
    "desc": "Node별 Pod CPU 사용량 (cores, 5분 rate)",
}

POD_TOTAL_CPU_USAGE_BY_NODE_AND_NS_5M = {
    "query": (
        "sum("
        "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m"
        '{{cluster="", node="{node}", namespace="{namespace}"}}'
        ")"
    ),
    "desc": "Node + Namespace별 Pod CPU 사용량 (cores, 5분 rate)",
}

POD_TOTAL_MEMORY_USAGE_ALL = {
    "query": (
        "sum(" "container_memory_working_set_bytes" '{{cluster="", container!=""}}' ")"
    ),
    "desc": "전체 클러스터 Pod Memory 사용량 (bytes)",
}

POD_TOTAL_MEMORY_USAGE_BY_NS = {
    "query": (
        "sum("
        "container_memory_working_set_bytes"
        '{{cluster="", container!="", namespace="{namespace}"}}'
        ")"
    ),
    "desc": "Namespace별 Pod Memory 사용량 (bytes)",
}

POD_TOTAL_MEMORY_USAGE_BY_NODE = {
    "query": (
        "sum("
        "container_memory_working_set_bytes"
        '{{cluster="", container!="", node="{node}"}}'
        ")"
    ),
    "desc": "Node별 Pod Memory 사용량 (bytes)",
}

POD_TOTAL_MEMORY_USAGE_BY_NODE_AND_NS = {
    "query": (
        "sum("
        "container_memory_working_set_bytes"
        '{{cluster="", container!="", node="{node}", namespace="{namespace}"}}'
        ")"
    ),
    "desc": "Node + Namespace별 Pod Memory 사용량 (bytes)",
}

CPU_USAGE_BY_POD_ALL_5M = {
    "query": (
        "sum by (pod) ("
        "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m"
        '{{cluster=""}}'
        ")"
    ),
    "desc": "전체 클러스터 Pod별 CPU 사용량 (cores, 5분 rate)",
}

CPU_USAGE_BY_POD_NS_5M = {
    "query": (
        "sum by (pod) ("
        "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m"
        '{{cluster="", namespace="{namespace}"}}'
        ")"
    ),
    "desc": "Namespace 내 Pod별 CPU 사용량 (cores, 5분 rate)",
}

CPU_USAGE_BY_POD_NODE_5M = {
    "query": (
        "sum by (pod) ("
        "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m"
        '{{cluster="", node="{node}"}}'
        ")"
    ),
    "desc": "Node 내 Pod별 CPU 사용량 (cores, 5분 rate)",
}

CPU_USAGE_BY_POD_NODE_AND_NS_5M = {
    "query": (
        "sum by (pod) ("
        "node_namespace_pod_container:container_cpu_usage_seconds_total:sum_rate5m"
        '{{cluster="", node="{node}", namespace="{namespace}"}}'
        ")"
    ),
    "desc": "Node + Namespace 내 Pod별 CPU 사용량 (cores, 5분 rate)",
}

MEMORY_USAGE_BY_POD_ALL = {
    "query": (
        "sum by (pod) ("
        "container_memory_working_set_bytes"
        '{{cluster="", container!=""}}'
        ")"
    ),
    "desc": "전체 클러스터 Pod별 Memory 사용량 (bytes)",
}

MEMORY_USAGE_BY_POD_NS = {
    "query": (
        "sum by (pod) ("
        "container_memory_working_set_bytes"
        '{{cluster="", container!="", namespace="{namespace}"}}'
        ")"
    ),
    "desc": "Namespace 내 Pod별 Memory 사용량 (bytes)",
}

MEMORY_USAGE_BY_POD_NODE = {
    "query": (
        "sum by (pod) ("
        "container_memory_working_set_bytes"
        '{{cluster="", container!="", node="{node}"}}'
        ")"
    ),
    "desc": "Node 내 Pod별 Memory 사용량 (bytes)",
}

MEMORY_USAGE_BY_POD_NODE_AND_NS = {
    "query": (
        "sum by (pod) ("
        "container_memory_working_set_bytes"
        '{{cluster="", container!="", node="{node}", namespace="{namespace}"}}'
        ")"
    ),
    "desc": "Node + Namespace 내 Pod별 Memory 사용량 (bytes)",
}

NETWORK_RX_BY_POD_ALL_1M = {
    "query": (
        "sum by (pod) ("
        "rate(container_network_receive_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster=""}}[1m])'
        ")"
    ),
    "desc": "전체 클러스터 Pod별 Network 수신량 (bytes/s, 1분 rate)",
}

NETWORK_RX_BY_POD_NS_1M = {
    "query": (
        "sum by (pod) ("
        "rate(container_network_receive_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", namespace="{namespace}"}}[1m])'
        ")"
    ),
    "desc": "Namespace 내 Pod별 Network 수신량 (bytes/s, 1분 rate)",
}

NETWORK_RX_BY_POD_NODE_1M = {
    "query": (
        "sum by (pod) ("
        "rate(container_network_receive_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", node="{node}"}}[1m])'
        ")"
    ),
    "desc": "Node 내 Pod별 Network 수신량 (bytes/s, 1분 rate)",
}

NETWORK_RX_BY_POD_NODE_AND_NAMESPACE_1M = {
    "query": (
        "sum by (pod) ("
        "rate(container_network_receive_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", namespace="{namespace}", node="{node}"}}[1m])'
        ")"
    ),
    "desc": "Node + Namespace 내 Pod별 Network 수신량 (bytes/s, 1분 rate)",
}

NETWORK_TX_BY_POD_ALL_1M = {
    "query": (
        "sum by (pod) ("
        "rate(container_network_transmit_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster=""}}[1m])'
        ")"
    ),
    "desc": "전체 클러스터 Pod별 Network 송신량 (bytes/s, 1분 rate)",
}

NETWORK_TX_BY_POD_NS_1M = {
    "query": (
        "sum by (pod) ("
        "rate(container_network_transmit_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", namespace="{namespace}"}}[1m])'
        ")"
    ),
    "desc": "Namespace 내 Pod별 Network 송신량 (bytes/s, 1분 rate)",
}

NETWORK_TX_BY_POD_NODE_1M = {
    "query": (
        "sum by (pod) ("
        "rate(container_network_transmit_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", node="{node}"}}[1m])'
        ")"
    ),
    "desc": "Node 내 Pod별 Network 송신량 (bytes/s, 1분 rate)",
}

NETWORK_TX_BY_POD_NODE_AND_NS_1M = {
    "query": (
        "sum by (pod) ("
        "rate(container_network_transmit_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", namespace="{namespace}", node="{node}"}}[1m])'
        ")"
    ),
    "desc": "Node + Namespace 내 Pod별 Network 송신량 (bytes/s, 1분 rate)",
}
