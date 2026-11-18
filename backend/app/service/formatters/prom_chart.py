from utils.time_utils import format_ts

def prom_range_to_chart(
    result,
    label_key="namespace",
    default_name="value",
    round_digits=0,
):

    series = []

    if not result:
        return series

    for item in result:
        if not isinstance(item, dict):
            continue

        metric = item.get("metric") or {}

        name = metric.get(label_key) or default_name

        values = item.get("values", [])
        if not values:
            continue

        data = [
            [format_ts(ts), round(float(val), round_digits)]
            for ts, val in values
        ]

        series.append({
            "name": name,
            "data": data
        })

    return series
