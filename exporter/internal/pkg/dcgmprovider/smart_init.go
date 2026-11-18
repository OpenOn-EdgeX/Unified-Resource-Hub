// Adapted for Unified Resource Hub. See NOTICE.
package dcgmprovider

import (
	"fmt"
	"log/slog"
	"os"
	"testing"

	"github.com/NVIDIA/go-dcgm/pkg/dcgm"
	"gpu-exporter/internal/pkg/appconfig"
)

func SmartDCGMInit(t *testing.T, config *appconfig.Config) {
	t.Helper()

	if Client() != nil {
		slog.Info("DCGM already initialized")
		return
	}

	client := dcgmProvider{}

	config.UseRemoteHE = false
	if config.EnableDCGMLog {
		os.Setenv("__DCGM_DBG_FILE", "-")
		os.Setenv("__DCGM_DBG_LVL", config.DCGMLogLevel)
	}

	slog.Info("Attempting to initialize DCGM in embedded mode.")
	cleanup, err := dcgm.Init(dcgm.Embedded)
	if err != nil {
		slog.Info("Embedded DCGM failed, trying remote host engine")

		config.UseRemoteHE = true
		config.RemoteHEInfo = "localhost:5555"

		slog.Info("Attempting to connect to remote hostengine at " + config.RemoteHEInfo)
		cleanup, err = dcgm.Init(dcgm.Standalone, config.RemoteHEInfo, "0")
		if err != nil {
			if cleanup != nil {
				cleanup()
			}
			slog.Error(fmt.Sprintf("Both embedded and remote DCGM failed: %v", err))
			t.Skip("Skipping test - DCGM initialization failed for both embedded and remote modes")
			return
		}
	} else {
		slog.Info("Embedded DCGM initialized successfully")
	}

	client.shutdown = cleanup

	if val := dcgm.FieldsInit(); val < 0 {
		slog.Error(fmt.Sprintf("Failed to initialize DCGM Fields module; err: %d", val))
		client.shutdown()
		t.Skip("Skipping test - DCGM Fields module initialization failed")
		return
	} else {
		slog.Info("Initialized DCGM Fields module.")
	}

	SetClient(client)
}
