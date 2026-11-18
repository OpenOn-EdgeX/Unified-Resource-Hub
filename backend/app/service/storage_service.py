from http import HTTPStatus
from typing import Optional
from app.repository import k8s_repo
from utils.parse_utils import format_bytes_si
from utils.parse_utils import parse_resource_to_bytes
from utils.time_utils import format_relative_time, KST
from utils.event_utils import build_event_summary
from app.exceptions import ApiException

NONE_DISPLAY = "-"

def namespace_list() -> dict:
    try:
        namespaces = k8s_repo.list_active_namespaces()
        ns_list = ["all"]
        ns_list.extend(n.metadata.name for n in namespaces)

        return {"namespace_list": ns_list}

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch storage namespace list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="STORAGE_NAMESPACE_LIST_FETCH_FAILED",
        ) from exc

def pvc_status(namespace_name: str) -> dict:
    try:
        ns = None if namespace_name == "all" else namespace_name
        pvcs = k8s_repo.list_pvcs(ns)

        total = 0
        bound = 0
        pending = 0
        lost = 0

        capacity_total = 0

        for pvc in pvcs:
            status = pvc.status
            phase = status.phase

            total += 1

            if phase == "Bound":
                bound += 1
            elif phase == "Pending":
                pending += 1
            elif phase == "Lost":
                lost += 1

            if phase != "Bound":
                continue

            capacity = status.capacity or {}
            cap_storage = capacity.get("storage")
            if cap_storage:
                capacity_total += parse_resource_to_bytes(cap_storage)

        return {
            "total_pvc": total,
            "bound": bound,
            "pending": pending,
            "lost": lost,
            "capacity": format_bytes_si(capacity_total, precision=1),

        }

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch PVC summary",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="STORAGE_PVC_SUMMARY_FETCH_FAILED",
        ) from exc

def pvc_list(namespace_name: str) -> list:
    try:
        ns = None if namespace_name == "all" else namespace_name
        pvcs = k8s_repo.list_pvcs(ns)

        result = []
        for pvc in pvcs:
            metadata = pvc.metadata
            spec = pvc.spec
            status = pvc.status

            name = metadata.name

            namespace = metadata.namespace

            phase = status.phase

            sc = _get_storage_class(pvc)

            created = metadata.creation_timestamp

            volume_name = spec.volume_name

            if volume_name:
                capacity = (status.capacity or {}).get("storage")
                mode = _parse_access_modes(status.access_modes)

            else:
                capacity = None
                mode = None
                volume_name = None

            result.append(
                {
                    "name": name or NONE_DISPLAY,
                    "namespace": namespace or NONE_DISPLAY,
                    "status": phase or NONE_DISPLAY,
                    "storage_class": sc or NONE_DISPLAY,
                    "capacity": capacity or "0" if volume_name else NONE_DISPLAY,

                    "access_mode": mode or NONE_DISPLAY,
                    "volume": volume_name or NONE_DISPLAY,
                    "age": format_relative_time(created) or NONE_DISPLAY,
                }
            )

        return result

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch PVC list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="STORAGE_PVC_LIST_FETCH_FAILED",
        ) from exc

def pvc_capacity(namespace_name: str, pvc_name: str) -> dict:
    return {}

def pvc_bound_volume(namespace_name: str, pvc_name: str) -> dict:
    try:
        pvc = k8s_repo.get_pvc(namespace_name, pvc_name)

        pvc_status = pvc.status
        pvc_phase = pvc_status.phase
        pvc_spec = pvc.spec
        volume = pvc_spec.volume_name

        if pvc_phase != "Bound" or not volume:
            return {}

        pv = k8s_repo.get_pv(volume)

        if not pv:
            return {}

        metadata = pv.metadata
        spec = pv.spec

        name = metadata.name

        volume_id = _get_volume_id(spec)

        capacity = (spec.capacity or {}).get("storage")

        sc = _get_storage_class(pv)

        mode = _parse_access_modes(spec.access_modes)

        reclaim_policy = spec.persistent_volume_reclaim_policy

        backend_type = _detect_pv_backend(spec)

        created = metadata.creation_timestamp

        return {
            "name": name or NONE_DISPLAY,
            "capacity": capacity or NONE_DISPLAY,
            "storage_class": sc or NONE_DISPLAY,
            "access_mode": mode or NONE_DISPLAY,
            "volume_id": volume_id or NONE_DISPLAY,
            "reclaim_policy": reclaim_policy or NONE_DISPLAY,
            "backend_type": backend_type or NONE_DISPLAY,
            "created": _format_creation_kst(created) or NONE_DISPLAY,

        }

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch PVC bound volume",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="STORAGE_PVC_BOUND_VOLUME_FETCH_FAILED",
        ) from exc

def pvc_connected_pods(namespace_name: str, pvc_name: str) -> list:
    try:

        pods = k8s_repo.list_pods(namespace_name)

        present_kinds = _pod_owner_kinds_present(pods, {"ReplicaSet", "Job"})

        rs_to_higher = {}
        if "ReplicaSet" in present_kinds:
            rs_list = k8s_repo.list_replica_sets(namespace_name)
            rs_to_higher = _build_higher_kind_mapping(rs_list, "Deployment")

        job_to_higher = {}
        if "Job" in present_kinds:
            job_list = k8s_repo.list_jobs(namespace_name)
            job_to_higher = _build_higher_kind_mapping(job_list, "CronJob")

        result = []
        for pod in pods:
            metadata = pod.metadata
            spec = pod.spec

            pod_name = metadata.name

            volumes = spec.volumes or []
            matching_volume_names = []
            for vol in volumes:

                pvc_ref = vol.persistent_volume_claim
                if pvc_ref and pvc_ref.claim_name == pvc_name:
                    matching_volume_names.append(vol.name)
                    continue

                if vol.ephemeral and pod_name:
                    auto_pvc_name = f"{pod_name}-{vol.name}"
                    if auto_pvc_name == pvc_name:
                        matching_volume_names.append(vol.name)

            if not matching_volume_names:
                continue

            node_name = spec.node_name

            init_containers = spec.init_containers or []
            main_containers = spec.containers

            mount_paths = set()
            for c in init_containers + main_containers:
                for mount in c.volume_mounts or []:
                    if mount.name in matching_volume_names:
                        mount_paths.add(mount.mount_path)

            mount_path = ", ".join(mount_paths) if mount_paths else None

            owner_refs = metadata.owner_references or []
            owner = next(
                (r for r in owner_refs if r.controller),
                owner_refs[0] if owner_refs else None,
            )
            if owner:
                if owner.kind == "ReplicaSet":
                    workload_kind = rs_to_higher.get(owner.name) or "ReplicaSet"
                elif owner.kind == "Job":
                    workload_kind = job_to_higher.get(owner.name) or "Job"
                else:
                    workload_kind = owner.kind
            else:

                workload_kind = None

            result.append(
                {
                    "pod_name": pod_name or NONE_DISPLAY,
                    "workload": workload_kind or NONE_DISPLAY,
                    "node": node_name or NONE_DISPLAY,
                    "mount_path": mount_path or NONE_DISPLAY,
                }
            )

        return result

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch PVC connected pods",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="STORAGE_PVC_CONNECTED_PODS_FETCH_FAILED",
        ) from exc

def pvc_events(namespace_name: str, pvc_name: str) -> dict:
    try:
        raw = k8s_repo.list_events_by_pvc(namespace_name, pvc_name)
        return build_event_summary(raw)

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch PVC events",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="PVC_EVENTS_FETCH_FAILED",
        ) from exc

def pv_sc_status() -> dict:
    try:
        pvs = k8s_repo.list_pvs()
        scs = k8s_repo.list_storage_classes()

        total = 0
        available = 0
        bound = 0
        released = 0
        failed = 0

        capacity_total = 0

        for pv in pvs:
            status = pv.status
            spec = pv.spec

            phase = status.phase

            total += 1

            if phase == "Available":
                available += 1
            elif phase == "Bound":
                bound += 1
            elif phase == "Released":
                released += 1
            elif phase == "Failed":
                failed += 1

            cap_str = (spec.capacity or {}).get("storage")
            if cap_str:
                capacity_total += parse_resource_to_bytes(cap_str)

        return {
            "total_pv": total,
            "available": available,
            "bound": bound,
            "released": released,
            "failed": failed,
            "capacity": format_bytes_si(
                capacity_total, precision=1
            ),
            "total_storageclass": len(scs),
        }

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch PV·SC summary",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="STORAGE_PV_SC_SUMMARY_FETCH_FAILED",
        ) from exc

def pv_list() -> list:
    try:
        pvs = k8s_repo.list_pvs()

        result = []
        for pv in pvs:
            metadata = pv.metadata
            spec = pv.spec
            status = pv.status

            name = metadata.name

            phase = status.phase

            capacity = (spec.capacity or {}).get("storage")

            sc = _get_storage_class(pv)

            claim = _parse_claim(spec.claim_ref)

            mode = _parse_access_modes(spec.access_modes)

            reclaim_policy = spec.persistent_volume_reclaim_policy

            backend_type = _detect_pv_backend(spec)

            path_or_volume_handle = _get_volume_id(spec)

            created = metadata.creation_timestamp

            result.append(
                {
                    "name": name or NONE_DISPLAY,
                    "status": phase or NONE_DISPLAY,
                    "capacity": capacity or NONE_DISPLAY,
                    "storage_class": sc or NONE_DISPLAY,
                    "claim": claim or NONE_DISPLAY,
                    "access_mode": mode or NONE_DISPLAY,
                    "reclaim_policy": reclaim_policy or NONE_DISPLAY,
                    "backend_type": backend_type or NONE_DISPLAY,
                    "path_or_volume_handle": path_or_volume_handle or NONE_DISPLAY,
                    "age": format_relative_time(created) or NONE_DISPLAY,
                }
            )

        return result

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch PV list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="STORAGE_PV_LIST_FETCH_FAILED",
        ) from exc

def sc_list() -> list:
    try:
        pvs = k8s_repo.list_pvs()
        scs = k8s_repo.list_storage_classes()

        pv_count_by_sc = {}
        for pv in pvs:
            sc_name = _get_storage_class(pv)
            if sc_name:
                pv_count_by_sc[sc_name] = pv_count_by_sc.get(sc_name, 0) + 1

        result = []
        for sc in scs:
            metadata = sc.metadata

            name = metadata.name or NONE_DISPLAY

            annotations = metadata.annotations or {}
            is_default = (
                annotations.get("storageclass.kubernetes.io/is-default-class") == "true"
                or annotations.get("storageclass.beta.kubernetes.io/is-default-class")
                == "true"
            )
            display_name = f"{name} (default)" if is_default else name

            provisioner = sc.provisioner

            reclaim_policy = sc.reclaim_policy
            binding_mode = sc.volume_binding_mode
            allow_expansion = sc.allow_volume_expansion

            params = sc.parameters or {}
            params_str = (
                ", ".join(f"{k}={v}" for k, v in sorted(params.items()))
                if params
                else "-"
            )

            created = metadata.creation_timestamp

            result.append(
                {
                    "name": display_name,
                    "provisioner": provisioner or NONE_DISPLAY,
                    "reclaim_policy": reclaim_policy or "Delete",
                    "volume_binding_mode": binding_mode or "Immediate",
                    "allow_expansion": ("Yes" if allow_expansion else "No"),

                    "parameters": params_str,
                    "pv_count": pv_count_by_sc.get(name, 0),
                    "age": format_relative_time(created) or NONE_DISPLAY,
                }
            )

        return result

    except Exception as exc:
        raise ApiException(
            message="Failed to fetch StorageClass list",
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            code="STORAGE_SC_LIST_FETCH_FAILED",
        ) from exc

_ACCESS_MODE_SHORT = {
    "ReadWriteOnce": "RWO",
    "ReadOnlyMany": "ROX",
    "ReadWriteMany": "RWX",
    "ReadWriteOncePod": "RWOP",
}

def _parse_access_modes(modes) -> Optional[str]:
    if not modes:
        return None
    return ",".join(str(_ACCESS_MODE_SHORT.get(m, m)) for m in modes)

def _parse_claim(claim_ref) -> Optional[str]:
    if not claim_ref:
        return None
    namespace = claim_ref.namespace
    name = claim_ref.name
    if namespace and name:
        return f"{namespace}/{name}"
    return None

def _get_beta_class_annotation(obj) -> Optional[str]:
    metadata = obj.metadata
    annotations = metadata.annotations or {}
    return annotations.get("volume.beta.kubernetes.io/storage-class")

def _get_storage_class(obj) -> Optional[str]:
    return _get_beta_class_annotation(obj) or obj.spec.storage_class_name

def _detect_pv_backend(spec) -> Optional[str]:
    csi = spec.csi
    csi_driver = getattr(csi, "driver", None)

    if csi_driver == "ebs.csi.aws.com":
        return "AWS EBS"
    if spec.aws_elastic_block_store:
        return "AWS EBS"

    if csi_driver == "efs.csi.aws.com":
        return "AWS EFS"

    if csi_driver == "fsx.csi.aws.com":
        return "AWS FSx"

    if csi_driver == "nfs.csi.k8s.io":
        return "NFS"
    if spec.nfs:
        return "NFS"

    if spec.local or spec.host_path:
        return "local storage"

    return _detect_pv_backend_extended(spec)

def _get_volume_id(spec) -> Optional[str]:
    if spec is None:
        return None

    csi = spec.csi
    csi_driver = getattr(csi, "driver", None)

    if csi_driver == "ebs.csi.aws.com":
        return csi.volume_handle
    ebs = spec.aws_elastic_block_store
    if ebs:
        return ebs.volume_id

    if csi_driver == "efs.csi.aws.com":
        return csi.volume_handle

    if csi_driver == "fsx.csi.aws.com":
        return csi.volume_handle

    if csi_driver == "nfs.csi.k8s.io":

        attrs = csi.volume_attributes or {}
        server = attrs.get("server") or "-"
        share = attrs.get("share") or "-"
        if server and share:
            return f"{server}:{share}"

        handle = csi.volume_handle or ""
        parts = handle.split("#")
        if len(parts) >= 2 and parts[0] and parts[1]:
            return f"{parts[0]}:{parts[1]}"

        return handle if handle else None

    nfs = spec.nfs
    if nfs:
        server = nfs.server or "-"
        path = nfs.path or "-"
        return f"{server}:{path}"

    host_path = spec.host_path
    if host_path:
        path = host_path.path
        if not path:
            return None
        node = _get_local_node(spec)
        return f"{node}:{path}" if node else path

    local = spec.local
    if local:
        path = local.path
        if not path:
            return None
        node = _get_local_node(spec)
        return f"{node}:{path}" if node else path

    return _get_volume_id_extended(spec)

def _get_local_node(spec) -> Optional[str]:
    affinity = spec.node_affinity
    required = getattr(affinity, "required", None)
    if not required:
        return None

    terms = required.node_selector_terms or []
    for term in terms:
        exprs = term.match_expressions or []
        for expr in exprs:
            key = expr.key
            values = expr.values
            if key == "kubernetes.io/hostname" and values:
                return values[0]

    return None

def _format_creation_kst(dt) -> Optional[str]:
    if not dt or dt.tzinfo is None:
        return None

    kst_dt = dt.astimezone(KST)
    return kst_dt.strftime("%b %d, %Y %H:%M").replace(" 0", " ", 1)

def _pod_owner_kinds_present(pods, target_kinds: set) -> set:
    found = set()
    for pod in pods:
        metadata = pod.metadata
        for owner_ref in metadata.owner_references or []:
            if not owner_ref.controller:
                continue
            if owner_ref.kind in target_kinds:
                found.add(owner_ref.kind)
                if found == target_kinds:
                    return found
    return found

def _build_higher_kind_mapping(resources, target_higher_kind: str) -> dict:
    mapping = {}
    for resource in resources:
        metadata = resource.metadata
        name = metadata.name
        for owner_ref in metadata.owner_references or []:
            if not owner_ref.controller:
                continue
            if owner_ref.kind == target_higher_kind:
                mapping[name] = owner_ref.kind
                break
    return mapping

_CSI_DRIVER_LABELS = {

    "smb.csi.k8s.io": "SMB",

    "pd.csi.storage.gke.io": "GCE PD",
    "filestore.csi.storage.gke.io": "GCE Filestore",

    "disk.csi.azure.com": "Azure Disk",
    "file.csi.azure.com": "Azure File",

    "rbd.csi.ceph.com": "Ceph RBD",
    "cephfs.csi.ceph.com": "CephFS",
    "rook-ceph.rbd.csi.ceph.com": "Ceph RBD (Rook)",
    "rook-ceph.cephfs.csi.ceph.com": "CephFS (Rook)",

    "driver.longhorn.io": "Longhorn",
    "pxd.portworx.com": "Portworx",
    "csi.trident.netapp.io": "NetApp Trident",

    "cinder.csi.openstack.org": "Cinder",
    "csi.vsphere.vmware.com": "vSphere CSI",
}

def _detect_pv_backend_extended(spec) -> Optional[str]:

    csi = spec.csi
    if csi:
        driver = csi.driver
        if driver in _CSI_DRIVER_LABELS:
            return _CSI_DRIVER_LABELS[driver]
        return f"CSI: {driver or '-'}"

    if spec.azure_disk:
        return "Azure Disk"
    if spec.azure_file:
        return "Azure File"
    if spec.gce_persistent_disk:
        return "GCE PD"
    if spec.cinder:
        return "Cinder"

    if spec.iscsi:
        return "iSCSI"
    if spec.cephfs:
        return "CephFS"
    if spec.rbd:
        return "Ceph RBD"

    if spec.glusterfs:
        return "GlusterFS"
    if spec.vsphere_volume:
        return "vSphere"
    if spec.portworx_volume:
        return "Portworx"
    if spec.flex_volume:
        return "FlexVolume"
    if spec.quobyte:
        return "Quobyte"
    if spec.storageos:
        return "StorageOS"

    return None

def _get_volume_id_extended(spec) -> Optional[str]:
    csi = spec.csi
    if csi:
        return csi.volume_handle

    azure_disk = spec.azure_disk
    if azure_disk:
        return azure_disk.disk_uri

    azure_file = spec.azure_file
    if azure_file:
        return azure_file.share_name

    gce_pd = spec.gce_persistent_disk
    if gce_pd:
        return gce_pd.pd_name

    cinder = spec.cinder
    if cinder:
        return cinder.volume_id

    iscsi = spec.iscsi
    if iscsi:
        portal = iscsi.target_portal

        iqn = iscsi.iqn
        return f"{portal}/{iqn}" if portal and iqn else None

    cephfs = spec.cephfs
    if cephfs:
        monitors = cephfs.monitors or []
        monitor = monitors[0] if monitors else None
        path = cephfs.path
        return f"{monitor}:{path}" if monitor and path else None

    rbd = spec.rbd
    if rbd:
        monitors = rbd.monitors or []
        monitor = monitors[0] if monitors else None
        image = rbd.image
        return f"{monitor}/{image}" if monitor and image else None

    glusterfs = spec.glusterfs
    if glusterfs:
        endpoints = glusterfs.endpoints
        path = glusterfs.path
        return f"{endpoints}:{path}" if endpoints and path else None

    vsphere = spec.vsphere_volume
    if vsphere:
        return vsphere.volume_path

    portworx = spec.portworx_volume
    if portworx:
        return portworx.volume_id

    flex = spec.flex_volume
    if flex:
        return flex.driver
    quobyte = spec.quobyte
    if quobyte:
        return quobyte.volume

    storageos = spec.storageos
    if storageos:
        return storageos.volume_name

    return None
