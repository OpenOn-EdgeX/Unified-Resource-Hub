// Adapted for Unified Resource Hub. See NOTICE.
package server

import (
	"io"
	"log/slog"
	"net/http"
	"sync/atomic"
	"time"
)

var metricsRequestSequence atomic.Uint64

const requestTimeLayout = "2006-01-02T15:04:05.000000000Z07:00"

func serveWithRequestLog(w http.ResponseWriter, r *http.Request, next http.HandlerFunc) {
	received := time.Now()
	logger := slog.Default().With(
		slog.Uint64("request_id", metricsRequestSequence.Add(1)),
		slog.String("method", r.Method),
		slog.String("path", r.URL.Path),
	)
	logger.InfoContext(r.Context(), "HTTP request received",
		slog.String("received_at", received.Format(requestTimeLayout)))
	response := &requestLogWriter{ResponseWriter: w}
	returned := false
	defer func() {

		completed := time.Now()
		status := response.status
		outcome := "completed"
		level := slog.LevelInfo
		if !returned {
			outcome, level = "aborted", slog.LevelError
		} else if response.writeError != nil {
			outcome, level = "write_error", slog.LevelError
		} else {
			if status == 0 {
				status = http.StatusOK
			}
			if status >= 400 {
				outcome = "http_error"
			}
		}
		attrs := []slog.Attr{
			slog.String("received_at", received.Format(requestTimeLayout)),
			slog.String("response_completed_at", completed.Format(requestTimeLayout)),
			slog.Float64("duration_ms", float64(completed.Sub(received))/float64(time.Millisecond)),
			slog.Int("status", status),
			slog.Int("bytes", response.bytes),
			slog.String("outcome", outcome),
		}
		if response.writeError != nil {
			attrs = append(attrs, slog.String("write_error", response.writeError.Error()))
		}
		logger.LogAttrs(r.Context(), level, "HTTP response completed", attrs...)
	}()
	next(response, r)
	returned = true
}

type requestLogWriter struct {
	http.ResponseWriter
	status     int
	bytes      int
	writeError error
}

func (w *requestLogWriter) Unwrap() http.ResponseWriter { return w.ResponseWriter }

func (w *requestLogWriter) WriteHeader(status int) {
	if w.status != 0 {
		return
	}
	if status >= 200 {
		w.status = status
	}
	w.ResponseWriter.WriteHeader(status)
}

func (w *requestLogWriter) Write(body []byte) (int, error) {
	if w.status == 0 {

		w.status = http.StatusOK
	}
	n, err := w.ResponseWriter.Write(body)
	w.bytes += n
	if w.writeError == nil {
		w.writeError = err
		if err == nil && n < len(body) {
			w.writeError = io.ErrShortWrite
		}
	}
	return n, err
}
