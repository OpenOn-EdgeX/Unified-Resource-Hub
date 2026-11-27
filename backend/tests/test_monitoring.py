from datetime import timezone
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from app import create_app
from app.client import monitoring_client
from app.repository import k8s_repo
from app.service.formatters.prom_chart import prom_range_to_chart
from utils.time_utils import parse_kst_to_utc


class MonitoringTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = cls.app.test_client()

    def test_read_only_contract(self):
        paths = self.client.get('/rest/1.0/swagger.json').get_json()['paths']
        self.assertEqual(len(paths), 86)
        self.assertEqual({p.split('/')[1] for p in paths},
                         {'dashboard', 'cluster', 'node', 'workload', 'pod', 'service', 'storage', 'gpu'})
        for methods in paths.values():
            self.assertEqual(set(methods) - {'parameters'}, {'get'})
        self.assertEqual(self.client.post('/rest/1.0/dashboard/nodes').status_code, 405)

    def test_dashboard_nodes(self):
        condition = SimpleNamespace(type='Ready', status='True')
        node = SimpleNamespace(status=SimpleNamespace(conditions=[condition]))
        with patch.object(k8s_repo, 'list_nodes', return_value=[node]), \
             patch('app.service.dashboard_service.history', return_value=[]):
            result = self.client.get('/rest/1.0/dashboard/nodes')
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.get_json(), {'total_nodes': 1, 'ready_nodes': 1, 'data': []})

    def test_dashboard_distinguishes_missing_samples_from_zero(self):
        cases = (
            ('resource_usage', [None, 0.0, 0.2534],
             {'cpu_usage': None, 'memory_usage': 0.0, 'disk_usage': 25.34}),
            ('gpu_usage', [None, 0.0, 7.125, None],
             {'Compute': None, 'Memory': 0.0, 'Encode': 7.12, 'Decode': None}),
        )
        for path, samples, expected in cases:
            with self.subTest(path=path), patch('app.service.dashboard_service.instant', side_effect=samples):
                response = self.client.get('/rest/1.0/dashboard/' + path)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.get_json(), expected)

    def test_native_sidecar_detection(self):
        payload = b'{"items":[{"metadata":{"uid":"x"},"spec":{"initContainers":[{"name":"agent","restartPolicy":"Always"},{"name":"setup"}]}}]}'
        self.assertEqual(k8s_repo._build_sidecar_lookup(payload), {'x': {'agent'}})

    def test_series_format(self):
        raw = [{'metric': {'gpu': '0'}, 'values': [[0, '12.345']]}]
        self.assertEqual(prom_range_to_chart(raw, 'gpu', round_digits=2),
                         [{'name': '0', 'data': [['1970-01-01 09:00:00', 12.35]]}])
        self.assertEqual(parse_kst_to_utc('1970-01-01T09:00:00').timestamp(), 0)
        self.assertEqual(parse_kst_to_utc('1970-01-01T00:00:00Z').tzinfo, timezone.utc)

    def test_upstream_error(self):
        with patch.object(k8s_repo, 'list_nodes', side_effect=RuntimeError('private detail')):
            response = self.client.get('/rest/1.0/dashboard/nodes')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.get_json()['code'], 'DASHBOARD_NODES_FETCH_FAILED')
        self.assertNotIn('private detail', response.get_data(as_text=True))

    def test_bad_parameters(self):
        for path in ['/rest/1.0/gpu/core/sm_clock/node-1', '/rest/1.0/node/info/%22bad']:
            self.assertEqual(self.client.get(path).status_code, 400)

    def test_prometheus_range(self):
        with self.app.app_context(), patch.dict(self.app.config, PROMETHEUS_URL='http://localhost:9090'), \
             patch.object(monitoring_client, '_session_get') as session:
            session.return_value.get.return_value.json.return_value = {'status': 'success', 'data': {'result': []}}
            result = monitoring_client.prom_range_query('up', 60, 120, '60s')
            session.return_value.get.assert_called_once_with('http://localhost:9090/api/v1/query_range',
                params={'query': 'up', 'start': 60, 'end': 120, 'step': '60s'}, timeout=30)
        self.assertEqual(result['status'], 'success')
