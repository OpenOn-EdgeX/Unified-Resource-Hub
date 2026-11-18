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
package collector

import (
	"fmt"

	"gpu-exporter/internal/pkg/appconfig"
	"gpu-exporter/internal/pkg/counters"
	"gpu-exporter/internal/pkg/dcgmprovider"
	"gpu-exporter/internal/pkg/devicemonitoring"
	"gpu-exporter/internal/pkg/devicewatchlistmanager"
)

type baseExpCollector struct {
	deviceWatchList devicewatchlistmanager.WatchList
	counter         counters.Counter
	labelsCounters  []counters.Counter
	hostname        string
	config          *appconfig.Config
	cleanups        []func()
}

func (c *baseExpCollector) createMetric(
	labels map[string]string, mi devicemonitoring.Info, uuid string, val int,
) Metric {
	gpuModel := getGPUModel(mi.DeviceInfo, c.config.ReplaceBlanksInModelName)

	m := Metric{
		Counter:      c.counter,
		Value:        fmt.Sprint(val),
		UUID:         uuid,
		GPU:          fmt.Sprintf("%d", mi.DeviceInfo.GPU),
		GPUUUID:      mi.DeviceInfo.UUID,
		GPUDevice:    fmt.Sprintf("nvidia%d", mi.DeviceInfo.GPU),
		GPUModelName: gpuModel,
		GPUPCIBusID:  mi.DeviceInfo.PCI.BusID,
		Hostname:     c.hostname,

		Labels:     labels,
		Attributes: map[string]string{},
	}
	if mi.InstanceInfo != nil {
		m.MigProfile = mi.InstanceInfo.ProfileName
		m.GPUInstanceID = fmt.Sprintf("%d", mi.InstanceInfo.Info.NvmlInstanceId)
	} else {
		m.MigProfile = ""
		m.GPUInstanceID = ""
	}
	return m
}

func (c *baseExpCollector) getLabelsFromCounters(mi devicemonitoring.Info, labels map[string]string) error {
	latestValues, err := dcgmprovider.Client().EntityGetLatestValues(mi.Entity.EntityGroupId, mi.Entity.EntityId,
		c.deviceWatchList.LabelDeviceFields())
	if err != nil {
		return err
	}

	for _, val := range latestValues {
		v := toString(val)

		if v == skipDCGMValue {
			continue
		}

		counter, err := findCounterField(c.labelsCounters, val.FieldID)
		if err != nil {
			continue
		}

		if counter.IsLabel() {
			labels[counter.FieldName] = v
			continue
		}
	}
	return nil
}

func (c *baseExpCollector) Cleanup() {
	for _, cleanup := range c.cleanups {
		cleanup()
	}
}
