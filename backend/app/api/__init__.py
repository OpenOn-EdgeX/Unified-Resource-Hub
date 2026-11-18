from .dashboard_controller import dashboard_ns
from .cluster_controller import cluster_ns
from .node_controller import node_ns
from .pod_controller import pod_ns
from .workload_controller import workload_ns
from .service_controller import service_ns
from .storage_controller import storage_ns
from .gpu_controller import gpu_ns

namespaces = [
    (dashboard_ns, "/dashboard"),
    (cluster_ns, "/cluster"),
    (node_ns, "/node"),
    (pod_ns, "/pod"),
    (workload_ns, "/workload"),
    (service_ns, "/service"),
    (storage_ns, "/storage"),
    (gpu_ns, "/gpu"),
]
