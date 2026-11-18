// Adapted for Unified Resource Hub. See NOTICE.
package server

import (
	"bytes"
	"encoding/json"
	"errors"
	"io"
	"log/slog"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"
)

func captureRequestLogs(t *testing.T) *bytes.Buffer {
	t.Helper()
	var output bytes.Buffer
	previous := slog.Default()
	slog.SetDefault(slog.New(slog.NewJSONHandler(&output, nil)))
	t.Cleanup(func() { slog.SetDefault(previous) })
	return &output
}

func decodeRequestLogs(t *testing.T, output *bytes.Buffer) []map[string]any {
	t.Helper()
	decoder := json.NewDecoder(bytes.NewReader(output.Bytes()))
	var rows []map[string]any
	for {
		var row map[string]any
		if err := decoder.Decode(&row); err == io.EOF {
			return rows
		} else if err != nil {
			t.Fatal(err)
		}
		rows = append(rows, row)
	}
}

func TestRequestLogCapturesReceiptAndResponse(t *testing.T) {
	for _, status := range []int{http.StatusOK, http.StatusInternalServerError} {
		t.Run(http.StatusText(status), func(t *testing.T) {
			output := captureRequestLogs(t)
			w := httptest.NewRecorder()
			r := httptest.NewRequest(http.MethodGet, "/metrics?secret=not-logged", nil)
			r.Header.Set("Authorization", "secret-token")
			serveWithRequestLog(w, r, func(w http.ResponseWriter, r *http.Request) {
				rows := decodeRequestLogs(t, output)
				if len(rows) != 1 || rows[0]["msg"] != "HTTP request received" {
					t.Fatal("receipt was not logged before processing")
				}
				if status == http.StatusInternalServerError {
					http.Error(w, "collection failed", status)
					return
				}
				_, _ = io.WriteString(w, "metric 42\n")
			})
			rows := decodeRequestLogs(t, output)
			if len(rows) != 2 {
				t.Fatalf("got %d log rows", len(rows))
			}
			first, last := rows[0], rows[1]
			if first["request_id"] != last["request_id"] || last["status"] != float64(status) || last["bytes"] != float64(w.Body.Len()) {
				t.Fatalf("incorrect correlation/status/bytes: %v", rows)
			}
			start, err := time.Parse(time.RFC3339Nano, first["received_at"].(string))
			if err != nil {
				t.Fatal(err)
			}
			end, err := time.Parse(time.RFC3339Nano, last["response_completed_at"].(string))
			if err != nil {
				t.Fatal(err)
			}
			if end.Before(start) || last["duration_ms"].(float64) < 0 || first["received_at"] != last["received_at"] {
				t.Fatalf("invalid timing: %v", rows)
			}
			if w.Code != status || strings.Contains(output.String(), "secret") || last["path"] != "/metrics" {
				t.Fatalf("response modified or sensitive request data logged: %s", output.String())
			}
			if status == 500 && last["outcome"] != "http_error" {
				t.Fatalf("incorrect outcome: %v", last)
			}
		})
	}
}

type failingLogWriter struct{ http.ResponseWriter }

func (failingLogWriter) Write([]byte) (int, error) { return 2, errors.New("connection closed") }

func TestRequestLogCapturesPartialWriteFailure(t *testing.T) {
	output := captureRequestLogs(t)
	serveWithRequestLog(failingLogWriter{httptest.NewRecorder()}, httptest.NewRequest("GET", "/metrics", nil), func(w http.ResponseWriter, _ *http.Request) {
		n, err := w.Write([]byte("metric 42\n"))
		if n != 2 || err == nil {
			t.Fatal("writer error not preserved")
		}
	})
	rows := decodeRequestLogs(t, output)
	last := rows[len(rows)-1]
	if last["outcome"] != "write_error" || last["bytes"] != float64(2) || last["write_error"] != "connection closed" || last["level"] != "ERROR" {
		t.Fatalf("incorrect write failure log: %v", last)
	}
}

func TestRequestLogDoesNotHidePanic(t *testing.T) {
	output := captureRequestLogs(t)
	func() {
		defer func() {
			if recover() != http.ErrAbortHandler {
				t.Fatal("panic changed or swallowed")
			}
		}()
		serveWithRequestLog(httptest.NewRecorder(), httptest.NewRequest("GET", "/metrics", nil), func(http.ResponseWriter, *http.Request) { panic(http.ErrAbortHandler) })
	}()
	rows := decodeRequestLogs(t, output)
	if len(rows) != 2 || rows[1]["outcome"] != "aborted" || rows[1]["status"] != float64(0) {
		t.Fatalf("aborted request reported as success: %v", rows)
	}
}

func TestConcurrentRequestLogsHaveUniquePairs(t *testing.T) {
	output := captureRequestLogs(t)
	const requests = 24
	var wg sync.WaitGroup
	for i := 0; i < requests; i++ {
		wg.Add(1)
		go func() {
			defer wg.Done()
			serveWithRequestLog(httptest.NewRecorder(), httptest.NewRequest("GET", "/metrics", nil), func(w http.ResponseWriter, _ *http.Request) { _, _ = w.Write([]byte("ok")) })
		}()
	}
	wg.Wait()
	rows := decodeRequestLogs(t, output)
	pairs := map[float64][]string{}
	for _, row := range rows {
		id := row["request_id"].(float64)
		pairs[id] = append(pairs[id], row["msg"].(string))
	}
	if len(rows) != requests*2 || len(pairs) != requests {
		t.Fatalf("missing/duplicate IDs: %v", pairs)
	}
	for id, pair := range pairs {
		if len(pair) != 2 || pair[0] != "HTTP request received" || pair[1] != "HTTP response completed" {
			t.Fatalf("invalid pair %v: %v", id, pair)
		}
	}
}
