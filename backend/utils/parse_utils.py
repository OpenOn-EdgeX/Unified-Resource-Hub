import math


def parse_usage(resource_type: str, value: str):

    if resource_type == "cpu":
        return parse_cpu(value)
    if resource_type == "memory":
        return parse_resource_to_bytes(value)

    raise ValueError(f"Unsupported resource type: {resource_type}")

_QUANTITY_SUFFIX = {
    "m": 1e-3, "k": 1e3, "M": 1e6, "G": 1e9, "T": 1e12, "P": 1e15, "E": 1e18,
    "Ki": 1024, "Mi": 1024**2, "Gi": 1024**3, "Ti": 1024**4, "Pi": 1024**5, "Ei": 1024**6,
}

_CPU_DIVISOR = {"n": 1e9, "u": 1e6, "m": 1e3}

def _finite(value):
    if not math.isfinite(value) or value < 0:
        raise ValueError("Expected a finite, nonnegative quantity")
    return value


def parse_cpu(value: str) -> float:
    value = str(value).strip()
    for suffix, divisor in _CPU_DIVISOR.items():
        if value.endswith(suffix):
            return _finite(float(value[:-len(suffix)]) / divisor)
    for suffix, factor in _QUANTITY_SUFFIX.items():
        if value.endswith(suffix):
            return _finite(float(value[:-len(suffix)]) * factor)
    return _finite(float(value))


def parse_resource_to_bytes(value: str) -> int:
    value = str(value).strip()
    for suffix, factor in _QUANTITY_SUFFIX.items():
        if value.endswith(suffix):
            return int(_finite(float(value[:-len(suffix)]) * factor))
    return int(_finite(float(value)))


def add_quantities(left, right):
    if left is None or right is None:
        return None
    try:
        return _finite(left + right)
    except (ValueError, OverflowError):
        return None


def quantity_total(resource, values):
    try:
        return _finite(sum(parse_usage(resource, value) for value in values))
    except (ValueError, OverflowError):
        return None


def format_bytes_iec(value: float, precision: int = 2) -> str:

    for unit, factor in [
        ("TiB", 1024**4),
        ("GiB", 1024**3),
        ("MiB", 1024**2),
        ("KiB", 1024),
    ]:
        if value >= factor:
            return f"{format_number(value / factor, precision)} {unit}"

    return f"{int(value)} B"

def format_bytes_si(value: float, precision: int = 2) -> str:

    for unit, factor in [
        ("TB", 1000**4),
        ("GB", 1000**3),
        ("MB", 1000**2),
        ("kB", 1000),
    ]:
        if value >= factor:
            return f"{format_number(value / factor, precision)} {unit}"

    return f"{int(value)} B"

def format_bytes_per_sec_iec(value: float, precision: int = 2) -> str:

    for unit, factor in [
        ("TiB/s", 1024**4),
        ("GiB/s", 1024**3),
        ("MiB/s", 1024**2),
        ("KiB/s", 1024),
    ]:
        if value >= factor:
            return f"{format_number(value / factor, precision)} {unit}"
    return f"{format_number(value, precision)} B/s"

def format_iops_per_sec(value: float, precision: int = 2) -> str:

    for unit, factor in [
        ("Mio/s", 1000**2),
        ("kio/s", 1000),
    ]:
        if value >= factor:
            return f"{format_number(value / factor, precision)} {unit}"
    return f"{format_number(value, precision)} io/s"

def to_display_value(resource_type: str, value):

    if resource_type == "memory":

        return format_number(value / (1024**2))

    return format_number(value)

def format_number(value: float, precision: int = 3):

    rounded = round(value, precision)
    return int(rounded) if isinstance(rounded, float) and rounded.is_integer() else rounded

def format_bps(bytes_per_sec: float, precision: int = 1):

    bits_per_sec = bytes_per_sec * 8
    for unit, factor in [
        ("Gbps", 1000**3),
        ("Mbps", 1000**2),
        ("Kbps", 1000),
    ]:
        if bits_per_sec >= factor:
            return f"{round(bits_per_sec / factor, precision)} {unit}"
    return f"{round(bits_per_sec, precision)} bps"
