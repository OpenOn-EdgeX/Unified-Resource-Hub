//go:build linux

// Adapted for Unified Resource Hub. See NOTICE.
package cmd

import (
	"os"
	"testing"
)

func clearRequestLogEnvironment(t *testing.T) {
	t.Helper()
	const name = "GPU_EXPORTER_REQUEST_LOG"
	original, existed := os.LookupEnv(name)
	t.Cleanup(func() {
		var err error
		if existed {
			err = os.Setenv(name, original)
		} else {
			err = os.Unsetenv(name)
		}
		if err != nil {
			t.Errorf("restore %s: %v", name, err)
		}
	})
	if err := os.Unsetenv(name); err != nil {
		t.Fatal(err)
	}
}

func TestRequestLogDefaultsAndFlags(t *testing.T) {
	clearRequestLogEnvironment(t)
	for _, tc := range []struct {
		name string
		args []string
		want bool
	}{
		{name: "default-enabled", want: true},
		{name: "flag-false", args: []string{"--request-log=false"}, want: false},
		{name: "flag-true", args: []string{"--request-log=true"}, want: true},
		{name: "bare-flag", args: []string{"--request-log"}, want: true},
	} {
		t.Run(tc.name, func(t *testing.T) {
			cfg, err := parseAppConfig(tc.args...)
			if err != nil {
				t.Fatal(err)
			}
			if cfg.RequestLog != tc.want {
				t.Fatalf("RequestLog = %t, want %t", cfg.RequestLog, tc.want)
			}
		})
	}
}

func TestRequestLogEnvironmentAndFlagPrecedence(t *testing.T) {
	clearRequestLogEnvironment(t)
	for _, tc := range []struct {
		name string
		env  string
		args []string
		want bool
	}{
		{name: "environment-false", env: "false", want: false},
		{name: "environment-true", env: "true", want: true},
		{name: "flag-overrides-false", env: "false", args: []string{"--request-log=true"}, want: true},
		{name: "flag-overrides-true", env: "true", args: []string{"--request-log=false"}, want: false},
	} {
		t.Run(tc.name, func(t *testing.T) {
			t.Setenv("GPU_EXPORTER_REQUEST_LOG", tc.env)
			cfg, err := parseAppConfig(tc.args...)
			if err != nil {
				t.Fatal(err)
			}
			if cfg.RequestLog != tc.want {
				t.Fatalf("RequestLog = %t, want %t", cfg.RequestLog, tc.want)
			}
		})
	}
}
