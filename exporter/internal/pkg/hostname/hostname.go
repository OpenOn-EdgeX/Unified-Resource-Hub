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
package hostname

import (
	"net"

	"gpu-exporter/internal/pkg/appconfig"
	osinterface "gpu-exporter/internal/pkg/os"
)

var os osinterface.OS = osinterface.RealOS{}

func GetHostname(config *appconfig.Config) (string, error) {
	if config.Kubernetes {

		return getLocalHostname()
	}
	if config.UseRemoteHE {
		return parseRemoteHostname(config)
	}
	return getLocalHostname()
}

func parseRemoteHostname(config *appconfig.Config) (string, error) {

	host, _, err := net.SplitHostPort(config.RemoteHEInfo)
	if err != nil {

		host = config.RemoteHEInfo
	}
	return host, nil
}

func getLocalHostname() (string, error) {
	if nodeName := os.Getenv("NODE_NAME"); nodeName != "" {
		return nodeName, nil
	}
	hostname, err := os.Hostname()
	if err != nil {
		return "", err
	}
	return hostname, nil
}
