GPU_UTIL_METRIC = {
    "query": 'DCGM_FI_DEV_GPU_UTIL{Hostname="%s"}',
    "desc": "GPU 사용률 (%, gauge, 최근값/시계열)",
}

GPU_MEM_COPY_UTIL_METRIC = {
    "query": 'DCGM_FI_DEV_MEM_COPY_UTIL{Hostname="%s"}',
    "desc": "GPU Memory Copy 사용률 (%, gauge, 최근값/시계열)",
}

GPU_ENC_UTIL_METRIC = {
    "query": 'DCGM_FI_DEV_ENC_UTIL{Hostname="%s"}',
    "desc": "GPU Encoder 사용률 (%, gauge, 최근값/시계열)",
}

GPU_DEC_UTIL_METRIC = {
    "query": 'DCGM_FI_DEV_DEC_UTIL{Hostname="%s"}',
    "desc": "GPU Decoder 사용률 (%, gauge, 최근값/시계열)",
}

GPU_UTIL_AVG_5M = {
    "query": (
        'avg('
        'avg by (UUID) ('
        'avg_over_time(DCGM_FI_DEV_GPU_UTIL[5m])'
        ')'
        ')'
    ),
    "desc": "GPU 사용률 (%, 5분 평균, 전체 GPU 집계)",
}

GPU_MEM_COPY_UTIL_AVG_5M = {
    "query": (
        'avg('
        'avg by (UUID) ('
        'avg_over_time(DCGM_FI_DEV_MEM_COPY_UTIL[5m])'
        ')'
        ')'
    ),
    "desc": "GPU Memory Copy 사용률 (%, 5분 평균, 전체 GPU 집계)",
}

GPU_ENC_UTIL_AVG_5M = {
    "query": (
        'avg('
        'avg by (UUID) ('
        'avg_over_time(DCGM_FI_DEV_ENC_UTIL[5m])'
        ')'
        ')'
    ),
    "desc": "GPU Encoder 사용률 (%, 5분 평균, 전체 GPU 집계)",
}

GPU_DEC_UTIL_AVG_5M = {
    "query": (
        'avg('
        'avg by (UUID) ('
        'avg_over_time(DCGM_FI_DEV_DEC_UTIL[5m])'
        ')'
        ')'
    ),
    "desc": "GPU Decoder 사용률 (%, 5분 평균, 전체 GPU 집계)",
}

GPU_FB_FREE_METRIC = {
    "query": 'DCGM_FI_DEV_FB_FREE{Hostname="%s"}',
    "desc": "VRAM Free (MiB, gauge, 최근값/시계열)",
}

GPU_FB_USED_METRIC = {
    "query": 'DCGM_FI_DEV_FB_USED{Hostname="%s"}',
    "desc": "VRAM Used (MiB, gauge, 최근값/시계열)",
}

GPU_FB_RESERVED_METRIC = {
    "query": 'DCGM_FI_DEV_FB_RESERVED{Hostname="%s"}',
    "desc": "VRAM Reserved (MiB, gauge, 최근값/시계열)",
}

GPU_TEMP_METRIC = {
    "query": 'DCGM_FI_DEV_GPU_TEMP{Hostname="%s"}',
    "desc": "GPU 온도 (°C, gauge, 최근값/시계열)",
}

GPU_MEMORY_TEMP_METRIC = {
    "query": 'DCGM_FI_DEV_MEMORY_TEMP{Hostname="%s"}',
    "desc": "GPU Memory 온도 (°C, gauge, 최근값/시계열)",
}

GPU_POWER_DRAW_METRIC = {
    "query": 'DCGM_FI_DEV_POWER_USAGE{Hostname="%s"}',
    "desc": "GPU 소비 전력 (W, gauge, 최근값/시계열)",
}

GPU_SM_CLOCK_METRIC = {
    "query": 'DCGM_FI_DEV_SM_CLOCK{Hostname="%s"}',
    "desc": "GPU SM Clock (MHz, gauge, 최근값/시계열)",
}

GPU_MEM_CLOCK_METRIC = {
    "query": 'DCGM_FI_DEV_MEM_CLOCK{Hostname="%s"}',
    "desc": "GPU Memory Clock (MHz, gauge, 최근값/시계열)",
}

GPU_NVLINK_BW_METRIC = {
    "query": 'rate(DCGM_FI_DEV_NVLINK_BANDWIDTH_TOTAL{Hostname="%s"}[5m]) / 1000000000',
    "desc": "직전 5분 평균 NVLink 전체 lane 전송률 (B/s -> GB/s, 누적 counter를 rate(5m)로 정규화, 최근값/시계열)",
}

GPU_XID_ERRORS_METRIC = {
    "query": 'DCGM_FI_DEV_XID_ERRORS{Hostname="%s"}',
    "desc": "XID 에러 코드 및 에러 메세지 (XID 에러 코드 정수값 0~172, gauge, 최근값/시계열).",
}

GPU_PSTATE_METRIC = {
    "query": 'DCGM_FI_DEV_PSTATE{Hostname="%s"}',
    "desc": "GPU P-STATE (P-State 정수값 0~15, 최근값/시계열)",
}

GPU_PCI_REPLAY_METRIC = {
    "query": 'rate(DCGM_FI_DEV_PCIE_REPLAY_COUNTER{Hostname="%s"}[5m])',
    "desc": "직전 5분 평균 PCIe Replay 발생률 (float(회/초), 누적 counter를 rate(5m)로 정규화, 최근값/시계열)",
}

DCGM_VERSION_INFO = {
    "query": 'dcgm_build_info{instance=~"%s.*"}',
    "desc": "DCGM 버전 정보 (커스텀 메트릭)",
}

NODE_BOOT_TIME_INFO = {
    "query": 'node_boot_time_seconds{instance=~"%s.*"}',
    "desc": "Node 서버 부팅 시각 (Unix epoch seconds)",
}
