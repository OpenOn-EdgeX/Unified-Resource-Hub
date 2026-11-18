from app.client import monitoring_client
from utils.time_utils import to_epoch_seconds

def instant(query, time=None):
    return monitoring_client.prom_instant_value(query, time)

def instant_series(query, time=None):
    return monitoring_client.prom_instant_query(query, time)

def last_hour(query):
    return monitoring_client.prom_last_hour_per_min(query)

def history(query, start=None, end=None, step="60s"):

    if start is None or end is None:
        return monitoring_client.get_node_ratio_history(query)

    return monitoring_client.get_node_ratio_history(
        query=query,
        start=start,
        end=end,
        step=step,
        raw=True
    )

def history_auto_step(query: str, start_date: str, end_date: str):
    start_ts = to_epoch_seconds(start_date)
    end_ts = to_epoch_seconds(end_date)

    duration_days = (end_ts - start_ts) / 86400

    if duration_days <= 1:
        step = 60
    elif duration_days <= 10:
        step = 600
    elif duration_days <= 20:
        step = 1200
    elif duration_days <= 30:
        step = 1800
    else:
        step = 3600

    return history(
        query=query,
        start=start_ts,
        end=end_ts,
        step=step,
    )
