from typing import Optional, Dict, Any, List
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from flask import current_app
from datetime import datetime, timezone
from utils.time_utils import KST

_session: Optional[requests.Session] = None

def _format_kst_timestamp(ts: float) -> str:
    dt = datetime.fromtimestamp(ts, tz=KST)
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def _session_get() -> requests.Session:
    global _session
    if _session is None:
        s = requests.Session()
        retries = Retry(
            total=3, backoff_factor=0.3,
            status_forcelist=(429, 500, 502, 503, 504),
            allowed_methods=("GET",),
            raise_on_status=False,
        )
        s.mount("http://", HTTPAdapter(max_retries=retries))
        s.mount("https://", HTTPAdapter(max_retries=retries))
        _session = s
    return _session

def _base_url() -> str:
    url = current_app.config["PROMETHEUS_URL"]
    if not url:
        raise RuntimeError("Set PROMETHEUS_URL to enable metrics")
    return url.rstrip("/")

def prom_instant_query(query: str, time_param: Optional[str] = None) -> Dict[str, Any]:
    base = _base_url()
    params = {"query": query}
    if time_param:
        params["time"] = time_param
    try:
        resp = _session_get().get(f"{base}/api/v1/query", params=params, timeout=20)
        code = resp.status_code
        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            try:
                j = resp.json()
            except Exception:
                j = {"error": str(e)}
            return {"status": "error", "http_code": code, "data": j}
        return resp.json()
    except requests.RequestException as e:
        return {"status": "error", "http_code": 0, "data": {"error": str(e)}}

def _choose_series(series: List[Dict[str, Any]], prefer_prefix: Optional[str] = None) -> Dict[str, Any]:
    if not series:
        return {}
    if prefer_prefix is None:
        prefer_prefix = current_app.config.get("PREFERRED_INSTANCE_PREFIX", "")
    return next(
        (ts for ts in series if ts.get("metric", {}).get("instance", "").startswith(prefer_prefix)),
        series[0]
    )

def prom_instant_value(query: str, time_param: Optional[str] = None) -> Optional[float]:
    res = prom_instant_query(query, time_param)
    if res.get("status") != "success":
        return None
    series = res.get("data", {}).get("result", []) or []
    if not series:
        return None
    chosen = _choose_series(series)
    val_str = chosen.get("value", [None, "NaN"])[1]
    try:
        v = float(val_str)
        if not (v == v) or v in (float("inf"), float("-inf")):
            return None
        return v
    except Exception:
        return None

def prom_range_query(
    query: str,
    start: int,
    end: int,
    step: str = "60s"
):
    base = _base_url()
    params = {
        "query": query,
        "start": start,
        "end": end,
        "step": step,
    }

    try:
        resp = _session_get().get(
            f"{base}/api/v1/query_range",
            params=params,
            timeout=30
        )
        code = resp.status_code

        try:
            resp.raise_for_status()
        except requests.HTTPError as e:
            try:
                j = resp.json()
            except Exception:
                j = {"error": str(e)}
            return {"status": "error", "http_code": code, "data": j}

        return resp.json()

    except requests.RequestException as e:
        return {"status": "error", "http_code": 0, "data": {"error": str(e)}}

def _matrix_to_series_list(res: Dict[str, Any]) -> List[List[str]]:
    out: List[List[str]] = []
    if res.get("status") != "success":
        return out
    result = res.get("data", {}).get("result", []) or []
    if not result:
        return out

    values = result[0].get("values", []) or []
    for ts, v in values:
        out.append([_format_kst_timestamp(ts), v])
    return out

def prom_last_hour_per_min(query: str):
    end_ts = int(datetime.now(tz=timezone.utc).timestamp())
    start_ts = end_ts - 3600

    res = prom_range_query(
        query=query,
        start=start_ts,
        end=end_ts,
        step="60s"
    )

    return _matrix_to_series_list(res)

def get_node_ratio_history(query, start=None, end=None, step="60s", raw=False):
    if start is None or end is None:
        end = int(datetime.now(tz=timezone.utc).timestamp())
        start = end - 3600

    result = prom_range_query(query, start, end, step)
    if not result or result.get("status") != "success":
        return []

    if raw:
        return result.get("data", {}).get("result", [])

    data = []
    series = result.get("data", {}).get("result", [])
    if series:
        values = series[0].get("values", [])
        for ts, value in values:
            data.append([_format_kst_timestamp(ts), value])

    return data
