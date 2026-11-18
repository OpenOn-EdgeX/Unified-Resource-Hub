/*
 * Copyright (c) 2024, NVIDIA CORPORATION.  All rights reserved.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *      http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

// Adapted for Unified Resource Hub. See NOTICE.
package appconfig

import (
	"github.com/NVIDIA/go-dcgm/pkg/dcgm"
)

type KubernetesGPUIDType string

type DeviceOptions struct {
	Flex       bool
	MajorRange []int
	MinorRange []int
}

type DumpConfig struct {
	Enabled     bool   `yaml:"enabled" json:"enabled"`
	Directory   string `yaml:"directory" json:"directory"`
	Retention   int    `yaml:"retention" json:"retention"`
	Compression bool   `yaml:"compression" json:"compression"`
}

type Config struct {
	CollectorsFile                   string
	Address                          string
	CollectInterval                  int
	RequestLog                       bool
	Kubernetes                       bool
	KubernetesEnablePodLabels        bool
	KubernetesEnablePodUID           bool
	KubernetesGPUIdType              KubernetesGPUIDType
	KubernetesPodLabelAllowlistRegex []string
	KubernetesPodLabelCacheSize      int
	CollectDCP                       bool
	UseOldNamespace                  bool
	UseRemoteHE                      bool
	RemoteHEInfo                     string
	GPUDeviceOptions                 DeviceOptions
	SwitchDeviceOptions              DeviceOptions
	CPUDeviceOptions                 DeviceOptions
	NoHostname                       bool
	UseFakeGPUs                      bool
	ConfigMapData                    string
	MetricGroups                     []dcgm.MetricGroup
	WebSystemdSocket                 bool
	WebConfigFile                    string
	XIDCountWindowSize               int
	ReplaceBlanksInModelName         bool
	Debug                            bool
	ClockEventsCountWindowSize       int
	EnableDCGMLog                    bool
	DCGMLogLevel                     string
	PodResourcesKubeletSocket        string
	HPCJobMappingDir                 string
	NvidiaResourceNames              []string
	KubernetesVirtualGPUs            bool
	DumpConfig                       DumpConfig
	KubernetesEnableDRA              bool
	DisableStartupValidate           bool
}
