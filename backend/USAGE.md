# Monitoring API

From this directory, use Python 3.10 or later:

```sh
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
export KUBECONFIG=/path/to/read-only-kubeconfig
export PROMETHEUS_URL=http://localhost:9090
flask --app app:create_app run --host 127.0.0.1 --port 5000
```

Open `http://localhost:5000/ui/` for the dashboard. `GET /rest/1.0/swagger.json` lists the API. The `dashboard`, `cluster`, `node`, `pod`, `workload`, `service`, `storage` and `gpu` groups expose GET endpoints. Time-range queries require ISO 8601 `start_date` and `end_date`; times without an offset are interpreted as UTC+09:00. Chart timestamps use UTC+09:00.

Set `KUBECONFIG` explicitly outside Kubernetes. Without it, the client uses an in-cluster service account. Use read-only `get`/`list` access to nodes, namespaces, pods, events, workloads, services, endpoint slices, volumes, storage classes and pod metrics, plus version discovery as needed. No Secret access or write permissions are required. `CLUSTER_NAME` is an optional display label.

Point `PROMETHEUS_URL` at a trusted Prometheus endpoint. Time series depend on kube-state-metrics, kubelet/cAdvisor, node exporter, the recording rules in `app/query`, and optionally NVIDIA DCGM metrics. Verify exporter labels (such as `instance` and `Hostname`) against your setup. Missing series can produce empty, zero or placeholder values; these are not evidence that the resource is healthy. NPU telemetry and alert delivery are not implemented. No authentication layer is bundled: keep the server local or behind an authenticated TLS gateway; API responses contain live cluster inventory and events. For production use a WSGI server, not the Flask development server.

Offline tests (after installing dependencies):

```sh
python -m unittest discover -s tests -v
```
