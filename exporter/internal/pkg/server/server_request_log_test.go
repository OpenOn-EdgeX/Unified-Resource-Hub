// Adapted for Unified Resource Hub. See NOTICE.
package server

import (
	"strings"
	"testing"
)

func TestMetricsRequestLoggingCanBeDisabled(t *testing.T) {
	output := captureRequestLogs(t)
	s, _ := fixtureServer(t)
	s.config.RequestLog = false
	without := route(s, "/metrics")
	if strings.Contains(output.String(), "HTTP request received") || strings.Contains(output.String(), "HTTP response completed") {
		t.Fatal("request logs emitted while disabled")
	}
	s.config.RequestLog = true
	output.Reset()
	with := route(s, "/metrics")
	rows := decodeRequestLogs(t, output)
	if len(rows) != 2 || without.Code != with.Code || without.Body.String() != with.Body.String() || without.Header().Get("Content-Type") != with.Header().Get("Content-Type") {
		t.Fatalf("logging changed metrics response or did not log: %v", rows)
	}
}
