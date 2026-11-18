/*
 * Copyright (c) 2024, NVIDIA CORPORATION.  All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// Adapted for Unified Resource Hub. See NOTICE.
package server

import (
	"bytes"
	"context"
	"encoding/json"
	"fmt"
	"io"
	"log/slog"
	"net/http"
	"os"
	"sync"
	"time"

	"github.com/gorilla/mux"
	"github.com/prometheus/exporter-toolkit/web"
	"gpu-exporter/internal/pkg/appconfig"
	"gpu-exporter/internal/pkg/debug"
	"gpu-exporter/internal/pkg/devicewatchlistmanager"
	"gpu-exporter/internal/pkg/logging"
	"gpu-exporter/internal/pkg/registry"
	"gpu-exporter/internal/pkg/rendermetrics"
	"gpu-exporter/internal/pkg/transformation"
	"gpu-exporter/internal/pkg/utils"
)

const (
	internalServerError   = "internal server error"
	prometheusContentType = "text/plain; version=0.0.4; charset=utf-8"
)

func NewMetricsServer(
	c *appconfig.Config,
	metrics chan string,
	deviceWatchListManager devicewatchlistmanager.Manager,
	registry *registry.Registry,
) (*MetricsServer, func(), error) {
	router := mux.NewRouter()

	fileDumper := debug.NewFileDumper(c.DumpConfig)

	serverv1 := &MetricsServer{
		server: &http.Server{
			Addr:         c.Address,
			Handler:      router,
			ReadTimeout:  10 * time.Second,
			WriteTimeout: 10 * time.Second,
		},
		webConfig: &web.FlagConfig{
			WebListenAddresses: &[]string{c.Address},
			WebSystemdSocket:   &c.WebSystemdSocket,
			WebConfigFile:      &c.WebConfigFile,
		},
		metricsChan:            metrics,
		metrics:                "",
		registry:               registry,
		config:                 c,
		transformations:        transformation.GetTransformations(c),
		deviceWatchListManager: deviceWatchListManager,
		fileDumper:             fileDumper,
	}
	router.HandleFunc("/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("X-Content-Type-Options", "nosniff")
		w.WriteHeader(http.StatusOK)
		_, err := w.Write([]byte(`<html>
			<head><title>GPU Exporter</title></head>
			<body>
			<h1>GPU Exporter</h1>
			<p><a href="./metrics">Metrics</a></p>
			</body>
			</html>`))
		if err != nil {
			slog.Error("Failed to write response.", slog.String(logging.ErrorKey, err.Error()))
			http.Error(w, internalServerError, http.StatusInternalServerError)
			return
		}
	})

	router.HandleFunc("/health", serverv1.Health)
	router.HandleFunc("/metrics", serverv1.Metrics)

	var podMapper *transformation.PodMapper
	for _, t := range serverv1.transformations {
		if pm, ok := t.(*transformation.PodMapper); ok {
			podMapper = pm
			break
		}
	}

	cleanup := func() {
		if podMapper != nil && c.KubernetesEnableDRA && podMapper.ResourceSliceManager != nil {
			slog.Info("Stopping ResourceSliceManager")
			podMapper.ResourceSliceManager.Stop()
		}
	}

	return serverv1, cleanup, nil
}

func (s *MetricsServer) Run(ctx context.Context, stop chan interface{}, wg *sync.WaitGroup) {
	defer wg.Done()
	ctx, cancel := context.WithCancel(ctx)
	defer cancel()

	var httpwg sync.WaitGroup
	httpwg.Add(1)
	go func() {
		defer httpwg.Done()
		slog.Info("Starting webserver")

		if s.config.DumpConfig.Enabled {
			slog.Info("Debug dumps enabled - runtime objects may be written to files for troubleshooting",
				slog.String("dump_directory", s.config.DumpConfig.Directory),
				slog.Int("retention_hours", s.config.DumpConfig.Retention),
				slog.Bool("compression_enabled", s.config.DumpConfig.Compression),
				slog.String("note", "Debug files may be created during operation and cleaned up automatically"))
		} else {
			slog.Debug("Debug dumps disabled - use --dump-enabled flag to enable file-based debugging")
		}

		if err := web.ListenAndServe(s.server, s.webConfig, slog.Default()); err != nil && err != http.ErrServerClosed {
			slog.Error("Failed to Listen and Server HTTP server.", slog.String(logging.ErrorKey, err.Error()))
			os.Exit(1)
		}
	}()

	httpwg.Add(1)
	go func() {
		defer httpwg.Done()

		ticker := time.NewTicker(1 * time.Hour)
		defer ticker.Stop()

		for {
			select {
			case <-stop:
				return
			case <-ctx.Done():
				return
			case <-ticker.C:
				if s.fileDumper != nil {
					if err := s.fileDumper.CleanupOldFiles(); err != nil {
						slog.Warn("Failed to cleanup old debug files", slog.String(logging.ErrorKey, err.Error()))
					}
				}
			}
		}
	}()

	select {
	case <-stop:
	case <-ctx.Done():
	}
	cancel()

	shutdownCtx, shutdownCancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer shutdownCancel()
	if err := s.server.Shutdown(shutdownCtx); err != nil {
		slog.Error("Failed to shutdown HTTP server.", slog.String(logging.ErrorKey, err.Error()))
		s.fatal()
	}

	if err := utils.WaitWithTimeout(&httpwg, 5*time.Second); err != nil {
		slog.Error("Failed waiting for HTTP server to shutdown.", slog.String(logging.ErrorKey, err.Error()))
		s.fatal()
	}
}

func (s *MetricsServer) fatal() {
	os.Exit(1)
}

func (s *MetricsServer) Metrics(w http.ResponseWriter, r *http.Request) {
	if s.config.RequestLog {
		serveWithRequestLog(w, r, s.serveMetrics)
		return
	}
	s.serveMetrics(w, r)
}

func (s *MetricsServer) serveMetrics(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Content-Type", prometheusContentType)
	payload, err := s.collectPayload(r.Context())
	if err != nil {
		slog.Error("Failed to collect metrics", slog.String(logging.ErrorKey, err.Error()))
		http.Error(w, internalServerError, http.StatusInternalServerError)
		return
	}
	if _, err := w.Write(payload); err != nil {
		slog.Error("Failed to write response.", slog.String(logging.ErrorKey, err.Error()))
	}
}

func (s *MetricsServer) collectPayload(ctx context.Context) ([]byte, error) {
	s.Lock()
	defer s.Unlock()
	if err := ctx.Err(); err != nil {
		return nil, err
	}
	metricGroups, err := s.registry.Gather()
	if err != nil {
		return nil, err
	}
	var buf bytes.Buffer
	if err := s.render(&buf, metricGroups); err != nil {
		return nil, err
	}

	meta := s.registry.GetCollectMeta()
	if meta != nil {
		buf.WriteString("# HELP dcgm_exporter_collect_duration_ms Time spent collecting metrics from DCGM/NVML (ms)\n")
		buf.WriteString("# TYPE dcgm_exporter_collect_duration_ms gauge\n")
		buf.WriteString(fmt.Sprintf(
			"dcgm_exporter_collect_duration_ms %.3f\n",
			meta.DurationMs,
		))

		buf.WriteString("# HELP dcgm_exporter_gpu_pstate GPU pstate captured at last collect\n")
		buf.WriteString("# TYPE dcgm_exporter_gpu_pstate gauge\n")
		buf.WriteString(fmt.Sprintf(
			"dcgm_exporter_gpu_pstate %d\n",
			meta.GPUPstate,
		))

		buf.WriteString("# HELP dcgm_build_info DCGM build and version info\n")
		buf.WriteString("# TYPE dcgm_build_info gauge\n")
		buf.WriteString(fmt.Sprintf(
			"dcgm_build_info{dcgm_version=%q} 1\n",
			meta.DCGMVersion,
		))
	}

	return buf.Bytes(), nil
}

func (s *MetricsServer) render(w io.Writer, metricGroups registry.MetricsByCounterGroup) error {
	for group, metrics := range metricGroups {
		deviceWatchList, exists := s.deviceWatchListManager.EntityWatchList(group)
		if exists {

			var metricsFile, deviceInfoFile string
			var err error

			if s.fileDumper != nil {
				metricsFile, err = s.fileDumper.DumpToFile(metrics, "metrics", group.String())
				if err != nil {
					slog.Warn("Failed to write metrics debug file",
						slog.String(logging.ErrorKey, err.Error()),
						slog.String(logging.FieldEntityGroupKey, group.String()))
				}

				deviceInfoFile, err = s.fileDumper.DumpToFile(deviceWatchList.DeviceInfo(), "deviceinfo", group.String())
				if err != nil {
					slog.Warn("Failed to write device info debug file",
						slog.String(logging.ErrorKey, err.Error()),
						slog.String(logging.FieldEntityGroupKey, group.String()))
				}
			}

			slog.Debug("Applying transformations",
				slog.String(logging.FieldEntityGroupKey, group.String()),
				slog.Int("metrics_count", len(metrics)),
				slog.Int("transformations_count", len(s.transformations)),
				slog.String("metrics_debug_file", metricsFile),
				slog.String("deviceinfo_debug_file", deviceInfoFile),
			)

			for _, transformation := range s.transformations {
				transformErr := transformation.Process(metrics, deviceWatchList.DeviceInfo())
				if transformErr != nil {
					slog.LogAttrs(context.Background(), slog.LevelError, "Failed to apply transformations on metrics",
						slog.String(logging.ErrorKey, transformErr.Error()),
						slog.String(logging.FieldEntityGroupKey, group.String()),
						slog.String("transformation", transformation.Name()),
						slog.Int("metrics_count", len(metrics)),
						slog.String("metrics_debug_file", metricsFile),
						slog.String("deviceinfo_debug_file", deviceInfoFile),
					)
					return transformErr
				}
			}
			slog.Debug("Rendering metrics",
				slog.String(logging.FieldEntityGroupKey, group.String()),
				slog.Int("metrics_count", len(metrics)),
				slog.String("metrics_debug_file", metricsFile))
			err = rendermetrics.RenderGroup(w, group, metrics)
			if err != nil {
				slog.LogAttrs(context.Background(), slog.LevelError, "Failed to renderGroup metrics",
					slog.String(logging.ErrorKey, err.Error()),
					slog.String(logging.FieldEntityGroupKey, group.String()),
					slog.Int("metrics_count", len(metrics)),
					slog.String("metrics_debug_file", metricsFile),
					slog.String("deviceinfo_debug_file", deviceInfoFile),
				)
				return err
			}
		}
	}
	return nil
}

func (s *MetricsServer) Health(w http.ResponseWriter, _ *http.Request) {
	w.Header().Set("X-Content-Type-Options", "nosniff")
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	if _, err := w.Write([]byte("OK")); err != nil {
		slog.Error("Failed to write health response.", slog.String(logging.ErrorKey, err.Error()))
		return
	}
}

func (s *MetricsServer) DumpMetricsToJSON() ([]byte, error) {
	s.Lock()
	defer s.Unlock()
	metricGroups, err := s.registry.Gather()
	if err != nil {
		return nil, err
	}

	if len(metricGroups) == 0 {
		return json.Marshal(map[string]any{"error": "no metrics found"})
	}

	return json.MarshalIndent(metricGroups, "", "  ")
}
