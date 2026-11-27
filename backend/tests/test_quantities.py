import unittest
from types import SimpleNamespace as Obj
from unittest.mock import patch

from app.repository import k8s_repo as repo
from app.service import dashboard_service, node_service, pod_service, storage_service, workload_service
from utils.parse_utils import parse_cpu, parse_resource_to_bytes


def sample(name, cpu, memory):
    return {'metadata': {'namespace': 'ns', 'name': name}, 'containers': [{'usage': {'cpu': cpu, 'memory': memory}}]}


class QuantityTests(unittest.TestCase):
    def test_valid_and_invalid_units(self):
        self.assertEqual(parse_cpu('250m'), 0.25)
        self.assertEqual(parse_cpu('6432451n'), 0.006432451)
        self.assertEqual(parse_resource_to_bytes('1.5Gi'), 1610612736)
        self.assertEqual(parse_resource_to_bytes('2M'), 2000000)
        for parse in (parse_cpu, parse_resource_to_bytes):
            self.assertEqual(parse('0'), 0)
            for value in (None, '', 'bad', '-1', 'NaN', 'Infinity', '1e999', '1e308Gi'):
                with self.subTest(parse=parse.__name__, value=value), self.assertRaises(ValueError):
                    parse(value)

    def test_top_pods_omit_unusable_usage_keep_valid_siblings(self):
        records = [sample('bad', '1e999', '0'), sample('good', '125m', '0')]
        spec = Obj(spec=Obj(containers=[Obj(resources=Obj(requests={'cpu':'100m'}, limits={'cpu':'NaN'}))], init_containers=[]))
        with patch.object(repo, 'list_pod_metrics', return_value=records), patch.object(repo, 'get_pod_resources', return_value=spec):
            self.assertEqual(dashboard_service.cpu_top_5(), [
                {'pod_name': 'good', 'cpu_usage': 0.125, 'cpu_request': 0.1, 'cpu_limit': None}])

    def test_storage_summaries_preserve_counts_without_partial_total(self):
        for qty, expected in [('0','0 B'), ('2M','2 MB'), ('bad',None), (None,None)]:
            for kind in ('pv','pvc'):
                with self.subTest(qty=qty,kind=kind):
                    items = [Obj(status=Obj(phase='Bound', capacity={'storage': v}), spec=Obj(capacity={'storage': v})) for v in ('0',qty)]
                    with patch.object(repo,'list_pvs',return_value=items), patch.object(repo,'list_storage_classes',return_value=[]), patch.object(repo,'list_pvcs',return_value=items):
                        data = storage_service.pv_sc_status() if kind == 'pv' else storage_service.pvc_status('all')
                    self.assertEqual(data['bound'], 2)
                    self.assertEqual(data['capacity'], expected)

    def test_pod_node_and_workload_keep_other_resource_and_other_pods(self):
        owner = Obj(kind='StatefulSet', name='work', controller=True)
        def obj(name):
            return Obj(metadata=Obj(name=name, uid=name, namespace='ns', creation_timestamp=None, owner_references=[owner]),
                       spec=Obj(replicas=2, node_name='node'), status=Obj(container_statuses=[], ready_replicas=2))
        pods = [obj('a'),obj('b')]
        metrics = [sample('a','100m','bad'),sample('b','200m','0')]
        info = {'status':'Running','ready':'1/1','restarts':0,'last_restart_at':None}
        with patch.multiple(repo, **{k:(lambda *a, data=v, **kw:data) for k,v in {
                'list_pod_metrics':metrics,'list_pods_by_node_with_sidecar_lookup':(pods,{}),
                'list_pods_with_sidecar_lookup':(pods,{}),'list_pods':pods,'list_statefulsets':[obj('work')],
                'list_deployments':[],'list_daemonsets':[],'list_replica_sets':[]}.items()}), \
             patch.object(pod_service,'get_pod_info',return_value=info), \
             patch.object(node_service,'get_pod_info',return_value=info), \
             patch.object(workload_service,'get_pod_info',return_value=info):
            for rows,cpu,mem in [(pod_service.pod_list('ns','all'),'cpu','memory'),
                                 (node_service.running_pods('node'),'cpu_usage','memory_usage'),
                                 (workload_service.pod_list('ns','work'),'cpu','memory')]:
                self.assertEqual([(r[cpu],r[mem]) for r in rows], [(0.1,None),(0.2,'0 B')])
            row = workload_service.workload_list('ns')['statefulset'][0]
            self.assertAlmostEqual(row['cpu'],0.3)
            self.assertIsNone(row['memory'])
