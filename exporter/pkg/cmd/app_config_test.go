//go:build linux

// Adapted for Unified Resource Hub. See NOTICE.
package cmd

import (
	"github.com/urfave/cli/v2"

	"gpu-exporter/internal/pkg/appconfig"
)

func parseAppConfig(args ...string) (*appconfig.Config, error) {
	app := NewApp("test")
	var config *appconfig.Config
	app.Action = func(c *cli.Context) error {
		var err error
		config, err = contextToConfig(c)
		return err
	}
	err := app.Run(append([]string{"gpu-exporter"}, args...))
	return config, err
}
