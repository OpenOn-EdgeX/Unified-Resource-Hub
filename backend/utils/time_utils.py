from datetime import datetime, timedelta, timezone

KST = timezone(timedelta(hours=9))

def format_ts(ts):
    return datetime.fromtimestamp(float(ts), tz=KST).strftime("%Y-%m-%d %H:%M:%S")

def parse_kst_to_utc(ts: str) -> datetime:

    dt_kst = datetime.fromisoformat(ts)
    if dt_kst.tzinfo is None:
        dt_kst = dt_kst.replace(tzinfo=KST)

    return dt_kst.astimezone(timezone.utc)

def to_epoch_seconds(dt: datetime) -> int:
    if dt.tzinfo is None:
        raise ValueError("datetime must be timezone-aware")
    return int(dt.timestamp())

def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds}s"
    m, s = divmod(seconds, 60)
    if m < 60:
        return f"{m}m{s}s"
    h, m = divmod(m, 60)
    if h < 24:
        return f"{h}h{m}m"
    return f"{h // 24}d"

def format_relative_time(dt):
    if not dt:
        return None
    return format_duration(int((datetime.now(timezone.utc) - dt).total_seconds()))
