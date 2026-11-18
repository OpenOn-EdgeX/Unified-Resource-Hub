from datetime import datetime
from typing import Optional, Union
from app.repository import k8s_repo
from app.repository import prom_repo
from app.repository.prom_repo import instant, instant_series
from utils.time_utils import to_epoch_seconds, format_ts
from utils.parse_utils import format_number
from app.service.formatters.prom_chart import prom_range_to_chart
from app.query import gpu_query as gq
from app.exceptions import api_error

NONE_DISPLAY = "-"
Number = Union[int, float]

@api_error(
    message="Failed to fetch GPU node list",
    code="GPU_NODE_LIST_FETCH_FAILED",
)
def node_list() -> dict:
    nodes = k8s_repo.list_nodes()

    gpu_nodes = [node.metadata.name for node in nodes if has_gpu(node)]

    return {"node_list": gpu_nodes}

@api_error(
    message="Failed to fetch GPU status",
    code="GPU_STATUS_FETCH_FAILED",
)
def gpu_status(node_name: str) -> dict:

    model = NONE_DISPLAY

    gpu_usage: Union[int, str] = NONE_DISPLAY

    util_resp = instant_series(gq.GPU_UTIL_METRIC["query"] % node_name)
    util_series = util_resp.get("data", {}).get("result", []) or []

    if util_series:
        metric_labels = util_series[0].get("metric", {})
        model = metric_labels.get("modelName", NONE_DISPLAY)

        gpu_usage_val = util_series[0].get("value", [None, None])[1]
        try:
            gpu_usage = int(float(gpu_usage_val))
        except (TypeError, ValueError):
            gpu_usage = NONE_DISPLAY

    total_vram: Union[Number, str]
    used_vram: Union[Number, str]

    total_vram, used_vram, _, unit = _get_vram_usage(node_name)

    if unit == "N/A":
        total_vram = NONE_DISPLAY
        used_vram = NONE_DISPLAY
        unit = "GB"

    gpu_temp = _instant_int(gq.GPU_TEMP_METRIC["query"] % node_name)

    power_usage = _instant_int(gq.GPU_POWER_DRAW_METRIC["query"] % node_name)

    status = _map_xid_to_status_text(node_name)

    return {
        "model": model,
        "gpu_usage": f"{gpu_usage}%",
        "vram_usage": f"{used_vram} / {total_vram} {unit}",
        "gpu_temperature": f"{gpu_temp}°C",
        "power_usage": f"{power_usage}W",
        "status": status,
    }

@api_error(
    message="Failed to fetch GPU Utilization",
    code="GPU_CORE_GPU_UTILIZATION_FETCH_FAILED",
)
def gpu_utilization(node_name: str, start_utc: str, end_utc: str) -> dict:
    query = gq.GPU_UTIL_METRIC["query"] % node_name

    avg_val, max_val, series = _history_with_avg_max(query, start_utc, end_utc)

    return {
        "avg": f"{avg_val}%",
        "max": f"{max_val}%",
        "series": series,
    }

@api_error(
    message="Failed to fetch GPU SM Clock",
    code="GPU_CORE_SM_CLOCK_FETCH_FAILED",
)
def sm_clock(node_name: str, start_utc: str, end_utc: str) -> dict:
    query = gq.GPU_SM_CLOCK_METRIC["query"] % node_name

    sm_clock_val, series = _history_with_recent(query, start_utc, end_utc)

    return {
        "current": f"{sm_clock_val} MHz",
        "series": series,
    }

@api_error(
    message="Failed to fetch GPU P-State",
    code="GPU_CORE_P_STATE_FETCH_FAILED",
)
def p_state(node_name: str, start_utc: str, end_utc: str) -> dict:
    query = gq.GPU_PSTATE_METRIC["query"] % node_name

    pstate_val, series = _history_with_recent(query, start_utc, end_utc)

    return {
        "current": f"P{pstate_val}",
        "series": series,
    }

@api_error(
    message="Failed to fetch GPU Encoder Utilization",
    code="GPU_CORE_ENCODER_UTILIZATION_FETCH_FAILED",
)
def encoder_utilization(node_name: str, start_utc: str, end_utc: str) -> dict:
    query = gq.GPU_ENC_UTIL_METRIC["query"] % node_name

    enc_val, series = _history_with_recent(query, start_utc, end_utc)

    return {
        "current": f"{enc_val}%",
        "series": series,
    }

@api_error(
    message="Failed to fetch GPU Decoder Utilization",
    code="GPU_CORE_DECODER_UTILIZATION_FETCH_FAILED",
)
def decoder_utilization(node_name: str, start_utc: str, end_utc: str) -> dict:
    query = gq.GPU_DEC_UTIL_METRIC["query"] % node_name

    dec_val, series = _history_with_recent(query, start_utc, end_utc)

    return {
        "current": f"{dec_val}%",
        "series": series,
    }

@api_error(
    message="Failed to fetch GPU Memory Utilization",
    code="GPU_MEMORY_MEMORY_UTILIZATION_FETCH_FAILED",
)
def memory_utilization(node_name: str, start_utc: str, end_utc: str) -> dict:
    query = gq.GPU_MEM_COPY_UTIL_METRIC["query"] % node_name

    avg_val, max_val, series = _history_with_avg_max(query, start_utc, end_utc)

    return {
        "avg": f"{avg_val}%",
        "max": f"{max_val}%",
        "series": series,
    }

@api_error(
    message="Failed to fetch GPU VRAM Usage",
    code="GPU_MEMORY_VRAM_USAGE_FETCH_FAILED",
)
def vram_usage(node_name: str, start_utc: str, end_utc: str) -> dict:

    total_vram, used_vram, reserved_vram, unit = _get_vram_usage(node_name, end_utc)

    if unit == "N/A":
        display = f"{NONE_DISPLAY}G / {NONE_DISPLAY}GB"
    else:
        display = f"{used_vram}{unit[0]} / {total_vram}{unit}"

    return {
        "display": display,
        "total": total_vram,
        "used": used_vram,
        "reserved": reserved_vram,
    }

@api_error(
    message="Failed to fetch GPU Memory Clock",
    code="GPU_MEMORY_MEMORY_CLOCK_FETCH_FAILED",
)
def memory_clock(node_name: str, start_utc: str, end_utc: str) -> dict:
    query = gq.GPU_MEM_CLOCK_METRIC["query"] % node_name

    mem_clock_val, series = _history_with_recent(query, start_utc, end_utc)

    return {
        "current": f"{mem_clock_val} MHz",
        "series": series,
    }

@api_error(
    message="Failed to fetch GPU Temperature",
    code="GPU_THERMAL_GPU_TEMPERATURE_FETCH_FAILED",
)
def gpu_temperature(node_name: str, start_utc: str, end_utc: str) -> dict:
    query = gq.GPU_TEMP_METRIC["query"] % node_name

    gpu_temp_val, series = _history_with_recent(query, start_utc, end_utc)

    return {
        "current": f"{gpu_temp_val}°C",
        "series": series,
    }

@api_error(
    message="Failed to fetch GPU Memory Temperature",
    code="GPU_THERMAL_MEMORY_TEMPERATURE_FETCH_FAILED",
)
def memory_temperature(node_name: str, start_utc: str, end_utc: str) -> dict:
    query = gq.GPU_MEMORY_TEMP_METRIC["query"] % node_name

    mem_temp_val, series = _history_with_recent(query, start_utc, end_utc)

    return {
        "current": f"{mem_temp_val}°C",
        "series": series,
    }

@api_error(
    message="Failed to fetch GPU Power Usage",
    code="GPU_POWER_USAGE_FETCH_FAILED",
)
def power_usage(node_name: str, start_utc: str, end_utc: str) -> dict:
    query = gq.GPU_POWER_DRAW_METRIC["query"] % node_name

    avg_val, max_val, series = _history_with_avg_max(query, start_utc, end_utc)

    return {
        "avg": f"{avg_val}W",
        "max": f"{max_val}W",
        "series": series,
    }

@api_error(
    message="Failed to fetch GPU Health & Errors",
    code="GPU_HEALTH_ERRORS_FETCH_FAILED",
)
def health_errors(node_name: str, start_utc: str, end_utc: str) -> dict:
    xid_query = gq.GPU_XID_ERRORS_METRIC["query"] % node_name
    pci_query = gq.GPU_PCI_REPLAY_METRIC["query"] % node_name
    nvlink_query = gq.GPU_NVLINK_BW_METRIC["query"] % node_name

    xid_err_code, xid_err_msg = _get_gpu_xid_info(node_name, end_utc)
    xid_series = prom_range_to_chart(
        prom_repo.history_auto_step(xid_query, start_utc, end_utc),
        label_key="device",
        default_name="Unknown",
    )

    pci_rate, pci_series = _history_with_recent(
        pci_query, start_utc, end_utc, round_digits=2
    )

    nvlink_rate, nvlink_series = _history_with_recent(
        nvlink_query, start_utc, end_utc, round_digits=1
    )

    return {
        "xid_error": f"{xid_err_msg} ({xid_err_code})",
        "xid_series": xid_series,
        "pci_replay_counter": 0 if pci_rate == NONE_DISPLAY else pci_rate,
        "pci_series": pci_series,
        "nvlink_bandwidth": f"{nvlink_rate} GB/s",
        "nvlink_series": nvlink_series,
    }

@api_error(
    message="Failed to fetch GPU Info",
    code="GPU_INFO_FETCH_FAILED",
)
def gpu_info(node_name: str) -> dict:

    util_q = gq.GPU_UTIL_METRIC["query"] % node_name
    util_labels = _get_prom_metric_labels(util_q)

    gpu_uuid = util_labels.get("UUID", NONE_DISPLAY)
    pci_bus_id = util_labels.get("pci_bus_id", NONE_DISPLAY)
    driver_version = util_labels.get("DCGM_FI_DRIVER_VERSION", NONE_DISPLAY)

    dcgm_q = gq.DCGM_VERSION_INFO["query"] % node_name
    dcgm_labels = _get_prom_metric_labels(dcgm_q)

    dcgm_version = dcgm_labels.get("dcgm_version", NONE_DISPLAY)

    boot_time = NONE_DISPLAY
    boot_epoch = instant(gq.NODE_BOOT_TIME_INFO["query"] % node_name)
    if boot_epoch is not None:
        boot_time = format_ts(boot_epoch)

    return {
        "gpu_uuid": gpu_uuid,
        "pci_bus_id": pci_bus_id,
        "driver_version": driver_version,
        "dcgm_version": dcgm_version,
        "boot_time": boot_time,
    }

def has_gpu(node) -> bool:
    allocatable = node.status.allocatable or {}

    for key, value in allocatable.items():
        if "gpu" not in key.lower():
            continue

        try:
            if int(value) > 0:
                return True
        except (TypeError, ValueError):
            continue

    return False

def _get_prom_metric_labels(query: str, time: Optional[str] = None) -> dict:
    resp = instant_series(query, time=time)
    result = resp.get("data", {}).get("result", []) or []

    metric_labels = result[0].get("metric", {}) if result else {}

    return metric_labels

def _instant_int(query: str) -> Union[int, str]:
    raw = instant(query)

    if raw is None:
        return NONE_DISPLAY

    try:
        return round(raw)
    except (TypeError, ValueError):
        return NONE_DISPLAY

_XID_STATUS_MAP = {
    "0": "Healthy",
    "13": "Graphics Engine Exception",
    "31": "GPU Memory Page Fault",
    "43": "GPU stopped",
    "48": "Double Bit ECC Error",
    "79": "GPU lost",
}

def _map_xid_to_status_text(node_name: str) -> str:
    err_code, err_msg = _get_gpu_xid_info(node_name)

    if err_code == NONE_DISPLAY:
        return NONE_DISPLAY

    if err_code in _XID_STATUS_MAP:
        return _XID_STATUS_MAP[err_code]

    return err_msg if err_msg != NONE_DISPLAY else f"Unknown Error (XID {err_code})"

def _get_gpu_xid_info(
    node_name: str, end_utc: Optional[datetime] = None
) -> tuple[str, str]:

    query = gq.GPU_XID_ERRORS_METRIC["query"] % node_name
    end_epoch = str(int(to_epoch_seconds(end_utc))) if end_utc else None

    xid_labels = _get_prom_metric_labels(query, end_epoch)
    err_msg = xid_labels.get("err_msg", NONE_DISPLAY)
    err_code = xid_labels.get("err_code", NONE_DISPLAY)

    return (err_code, err_msg)

def _get_vram_usage(
    node_name: str, end_utc: Optional[datetime] = None
) -> tuple[Number, Number, Number, str]:

    end_epoch = str(int(to_epoch_seconds(end_utc))) if end_utc else None

    fb_used_mib = instant(gq.GPU_FB_USED_METRIC["query"] % node_name, time=end_epoch)
    fb_free_mib = instant(gq.GPU_FB_FREE_METRIC["query"] % node_name, time=end_epoch)
    fb_reserved_mib = instant(
        gq.GPU_FB_RESERVED_METRIC["query"] % node_name, time=end_epoch
    )

    return _format_bytes_vram_usage(fb_used_mib, fb_free_mib, fb_reserved_mib)

def _format_bytes_vram_usage(
    fb_used_mib: Optional[float],
    fb_free_mib: Optional[float],
    fb_reserved_mib: Optional[float],
) -> tuple[Number, Number, Number, str]:

    if fb_used_mib is None or fb_free_mib is None or fb_reserved_mib is None:
        return (0, 0, 0, "N/A")

    total_mib = fb_used_mib + fb_free_mib + fb_reserved_mib
    unit, factor = _vram_unit_factor(total_mib)

    total_bytes = total_mib * 1024 * 1024
    used_bytes = fb_used_mib * 1024 * 1024
    reserved_bytes = fb_reserved_mib * 1024 * 1024

    total_vram = format_number(total_bytes / factor, 0)
    used_vram = format_number(used_bytes / factor, 1)
    reserved_vram = format_number(reserved_bytes / factor, 1)

    return (total_vram, used_vram, reserved_vram, unit)

def _vram_unit_factor(total_mib: float) -> tuple[str, int]:
    total_bytes = total_mib * 1024 * 1024

    for unit, factor in [
        ("TB", 1024**4),
        ("GB", 1024**3),
        ("MB", 1024**2),
        ("KB", 1024),
    ]:
        if total_bytes >= factor:
            return (unit, factor)

    return ("B", 1)

def _history_with_avg_max(
    query: str,
    start_utc: str,
    end_utc: str,
    round_digits: int = 0,
) -> tuple[Union[Number, str], Union[Number, str], list]:

    raw_range = prom_repo.history_auto_step(query, start_utc, end_utc)

    if not raw_range:
        return NONE_DISPLAY, NONE_DISPLAY, []

    avg_val: Union[Number, str] = NONE_DISPLAY
    max_val: Union[Number, str] = NONE_DISPLAY

    values = [float(v) for _, v in raw_range[0].get("values", []) or []]
    if values:
        try:
            avg_raw = sum(values) / len(values)
            max_raw = max(values)

            if round_digits == 0:
                avg_val = round(avg_raw)
                max_val = round(max_raw)
            else:
                avg_val = round(avg_raw, round_digits)
                max_val = round(max_raw, round_digits)
        except (TypeError, ValueError):
            avg_val = NONE_DISPLAY
            max_val = NONE_DISPLAY

    series = prom_range_to_chart(
        raw_range,
        label_key="device",
        default_name="Unknown",
        round_digits=round_digits,
    )

    return (avg_val, max_val, series)

def _history_with_recent(
    query: str,
    start_utc: str,
    end_utc: str,
    round_digits: int = 0,
) -> tuple[Union[Number, str], list]:

    raw_range = prom_repo.history_auto_step(query, start_utc, end_utc)

    if not raw_range:
        return NONE_DISPLAY, []

    recent: Union[Number, str] = NONE_DISPLAY

    values = raw_range[0].get("values") or []
    if values:
        try:
            val_float = float(values[-1][1])
            recent = (
                round(val_float)
                if round_digits == 0
                else round(val_float, round_digits)
            )
        except (TypeError, ValueError):
            recent = NONE_DISPLAY

    series = prom_range_to_chart(
        raw_range,
        label_key="device",
        default_name="Unknown",
        round_digits=round_digits,
    )

    return (recent, series)
