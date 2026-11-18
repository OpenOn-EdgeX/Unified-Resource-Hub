// Adapted for Unified Resource Hub. See NOTICE.
package server

import (
	"context"
	"errors"
	"net/http"
	"net/http/httptest"
	"strconv"
	"strings"
	"sync"
	"sync/atomic"
	"testing"

	"github.com/NVIDIA/go-dcgm/pkg/dcgm"

	"gpu-exporter/internal/pkg/appconfig"
	"gpu-exporter/internal/pkg/collector"
	"gpu-exporter/internal/pkg/counters"
	"gpu-exporter/internal/pkg/devicewatchlistmanager"
	"gpu-exporter/internal/pkg/registry"
)

type fixtureCollector struct {
	calls atomic.Int64
	fail  atomic.Bool
	value atomic.Int64
}

var fixtureError = errors.New("synthetic collector failure")

func (c *fixtureCollector) GetMetrics() (collector.MetricsByCounter, error) {
	c.calls.Add(1)
	if c.fail.Load() {
		return nil, fixtureError
	}
	counter := counters.Counter{FieldName: "DCGM_FI_DEV_GPU_TEMP", PromType: "gauge", Help: "GPU temperature (fixture)"}
	return collector.MetricsByCounter{counter: {{Counter: counter, Value: strconv.FormatInt(c.value.Load(), 10), GPU: "0", UUID: "UUID", GPUUUID: "GPU-fixture", GPUDevice: "nvidia0", GPUModelName: "Fixture GPU", Labels: map[string]string{"namespace": "fixture"}}}}, nil
}
func (*fixtureCollector) Cleanup() {}
func (*fixtureCollector) GetCollectMeta() *collector.CollectMeta {
	return &collector.CollectMeta{DurationMs: 1.25, GPUPstate: 8, DCGMVersion: "fixture-3.3.9"}
}

type fixtureManager struct{ devicewatchlistmanager.Manager }

func (fixtureManager) EntityWatchList(dcgm.Field_Entity_Group) (devicewatchlistmanager.WatchList, bool) {
	return devicewatchlistmanager.WatchList{}, true
}

func fixtureServer(t *testing.T) (*MetricsServer, *fixtureCollector) {
	t.Helper()
	c := &fixtureCollector{}
	c.value.Store(42)
	reg := registry.NewRegistry()
	tuple := collector.EntityCollectorTuple{}
	tuple.SetEntity(dcgm.FE_GPU)
	tuple.SetCollector(c)
	reg.Register(tuple)
	s, cleanup, err := NewMetricsServer(&appconfig.Config{}, nil, fixtureManager{}, reg)
	if err != nil {
		t.Fatal(err)
	}
	t.Cleanup(cleanup)
	return s, c
}

func route(s *MetricsServer, path string) *httptest.ResponseRecorder {
	w := httptest.NewRecorder()
	s.server.Handler.ServeHTTP(w, httptest.NewRequest(http.MethodGet, path, nil))
	return w
}

func TestMetricsPreserveRenderingAndMetadata(t *testing.T) {
	s, c := fixtureServer(t)
	want := route(s, "/metrics")
	if want.Code != http.StatusOK {
		t.Fatalf("metrics status %d", want.Code)
	}
	for _, line := range []string{
		"# HELP DCGM_FI_DEV_GPU_TEMP GPU temperature (fixture)",
		"# TYPE DCGM_FI_DEV_GPU_TEMP gauge",
		`gpu="0",UUID="GPU-fixture"`, `namespace="fixture"`,
		"# TYPE dcgm_exporter_collect_duration_ms gauge", "dcgm_exporter_collect_duration_ms 1.250",
		"dcgm_exporter_gpu_pstate 8", `dcgm_build_info{dcgm_version="fixture-3.3.9"} 1`,
	} {
		if !strings.Contains(want.Body.String(), line) {
			t.Errorf("missing contract %q in %q", line, want.Body.String())
		}
	}
	for i := 0; i < 5; i++ {
		w := route(s, "/metrics")
		if w.Code != http.StatusOK || w.Body.String() != want.Body.String() || w.Header().Get("Content-Type") != prometheusContentType {
			t.Fatalf("metrics rendering mismatch: status=%d body=%q", w.Code, w.Body.String())
		}
	}
	if c.calls.Load() != 6 {
		t.Fatalf("expected one collection per metrics request, got %d", c.calls.Load())
	}
	if w := route(s, "/health"); w.Code != http.StatusOK || w.Body.String() != "OK" {
		t.Fatalf("health route %d %q", w.Code, w.Body.String())
	}
	if w := route(s, "/"); w.Code != http.StatusOK || !strings.Contains(w.Body.String(), "GPU Exporter") {
		t.Fatalf("index route %d", w.Code)
	}
	if c.calls.Load() != 6 {
		t.Fatal("non-metrics route invoked collector")
	}
}

func TestMetricsRequestCollectsUpdatedValue(t *testing.T) {
	s, c := fixtureServer(t)
	first := route(s, "/metrics")
	c.value.Store(43)
	second := route(s, "/metrics")
	if first.Code != http.StatusOK || second.Code != http.StatusOK || !strings.Contains(first.Body.String(), "} 42\n") || !strings.Contains(second.Body.String(), "} 43\n") {
		t.Fatalf("request did not reflect the current collection: first=%q second=%q", first.Body.String(), second.Body.String())
	}
	if c.calls.Load() != 2 {
		t.Fatalf("expected two collections, got %d", c.calls.Load())
	}
}

func TestCollectionFailurePropagatesAndNextRequestRecovers(t *testing.T) {
	s, c := fixtureServer(t)
	if w := route(s, "/metrics"); w.Code != http.StatusOK {
		t.Fatalf("initial status %d", w.Code)
	}
	c.fail.Store(true)
	if _, err := s.collectPayload(context.Background()); !errors.Is(err, fixtureError) {
		t.Fatalf("collection error not propagated: %v", err)
	}
	if w := route(s, "/metrics"); w.Code != http.StatusInternalServerError || strings.Contains(w.Body.String(), "DCGM_FI_DEV_GPU_TEMP") {
		t.Fatalf("failed request did not return an error: status=%d body=%q", w.Code, w.Body.String())
	}
	c.fail.Store(false)
	c.value.Store(43)
	if w := route(s, "/metrics"); w.Code != http.StatusOK || !strings.Contains(w.Body.String(), "} 43\n") {
		t.Fatalf("next request failed to recover: status=%d body=%q", w.Code, w.Body.String())
	}
	if c.calls.Load() != 4 {
		t.Fatalf("expected every attempt to collect, got %d", c.calls.Load())
	}
}

func TestConcurrentMetricsRequestsEachCollect(t *testing.T) {
	s, c := fixtureServer(t)
	const requests = 24
	var wg sync.WaitGroup
	for i := 0; i < requests; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			w := route(s, "/metrics")
			if w.Code != http.StatusOK || !strings.Contains(w.Body.String(), "} 42\n") {
				t.Errorf("concurrent request failed: status=%d body=%q", w.Code, w.Body.String())
			}
		}()
	}
	wg.Wait()
	if c.calls.Load() != requests {
		t.Fatalf("expected %d collections, got %d", requests, c.calls.Load())
	}
}

func TestCollectPayloadCancellationSkipsCollector(t *testing.T) {
	s, c := fixtureServer(t)
	ctx, cancel := context.WithCancel(context.Background())
	cancel()
	if _, err := s.collectPayload(ctx); !errors.Is(err, context.Canceled) {
		t.Fatalf("cancel error %v", err)
	}
	if c.calls.Load() != 0 {
		t.Fatal("collector called after cancellation")
	}
}
