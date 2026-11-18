NETWORK_RX_BY_SERVICE_1M = {
    "query": (
        "sum(rate(container_network_receive_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", namespace="{namespace}", pod=~"{pod_regex}"}}[1m]))'
    ),
    "desc": "Service별 Pod Network 수신량 (bytes/s, 1분 rate, Pod 기반 단위 합산)",
}

NETWORK_TX_BY_SERVICE_1M = {
    "query": (
        "sum(rate(container_network_transmit_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", namespace="{namespace}", pod=~"{pod_regex}"}}[1m]))'
    ),
    "desc": "Service별 Pod Network 송신량 (bytes/s, 1분 rate, Pod 기반 단위 합산)",
}

NETWORK_RX_STATUS_ALL_5M = {
    "query": (
        "sum(rate(container_network_receive_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", pod=~"{pod_regex}"}}[5m]))'
    ),
    "desc": "전체 네임스페이스 Service 네트워크 수신량 (bytes/s, 5분 rate, Pod 기반 단위 합산)",
}

NETWORK_RX_STATUS_NS_5M = {
    "query": (
        "sum(rate(container_network_receive_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", namespace="{namespace}", pod=~"{pod_regex}"}}[5m]))'
    ),
    "desc": "Namespace별 Service 네트워크 수신량 (bytes/s, 5분 rate, Pod 기반 단위 합산)",
}

NETWORK_TX_STATUS_ALL_5M = {
    "query": (
        "sum(rate(container_network_transmit_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", pod=~"{pod_regex}"}}[5m]))'
    ),
    "desc": "전체 네임스페이스 Service 네트워크 송신량 (bytes/s, 5분 rate, Pod 기반 단위 합산)",
}

NETWORK_TX_STATUS_NS_5M = {
    "query": (
        "sum(rate(container_network_transmit_bytes_total"
        '{{job="kubelet", metrics_path="/metrics/cadvisor", cluster="", namespace="{namespace}", pod=~"{pod_regex}"}}[5m]))'
    ),
    "desc": "Namespace별 Service 네트워크 송신량 (bytes/s, 5분 rate, Pod 기반 단위 합산)",
}
