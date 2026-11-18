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
package devicewatchlistmanager

import (
	"github.com/NVIDIA/go-dcgm/pkg/dcgm"

	"gpu-exporter/internal/pkg/appconfig"
	"gpu-exporter/internal/pkg/counters"
	"gpu-exporter/internal/pkg/deviceinfo"
	"gpu-exporter/internal/pkg/devicewatcher"
)

var DeviceTypesToWatch = []dcgm.Field_Entity_Group{
	dcgm.FE_GPU,
	dcgm.FE_SWITCH,
	dcgm.FE_LINK,
	dcgm.FE_CPU,
	dcgm.FE_CPU_CORE,
}

type WatchList struct {
	deviceInfo        deviceinfo.Provider
	deviceFields      []dcgm.Short
	deviceGroups      []dcgm.GroupHandle
	deviceFieldGroup  dcgm.FieldHandle
	labelDeviceFields []dcgm.Short
	watcher           devicewatcher.Watcher
	collectInterval   int64
}

func NewWatchList(
	deviceInfo deviceinfo.Provider, deviceFields, labelDeviceFields []dcgm.Short,
	watcher devicewatcher.Watcher, collectInterval int64,
) *WatchList {
	return &WatchList{
		deviceInfo:        deviceInfo,
		deviceFields:      deviceFields,
		labelDeviceFields: labelDeviceFields,
		watcher:           watcher,
		collectInterval:   collectInterval,
	}
}

func (d *WatchList) DeviceInfo() deviceinfo.Provider {
	return d.deviceInfo
}

func (d *WatchList) DeviceFields() []dcgm.Short {
	return d.deviceFields
}

func (d *WatchList) SetDeviceFields(deviceFields []dcgm.Short) {
	d.deviceFields = deviceFields
}

func (d *WatchList) LabelDeviceFields() []dcgm.Short {
	return d.labelDeviceFields
}

func (d *WatchList) IsEmpty() bool {
	return len(d.deviceFields) == 0
}

func (d *WatchList) Watch() ([]func(), error) {
	var cleanups []func()
	var err error

	d.deviceGroups, d.deviceFieldGroup, cleanups, err = d.watcher.WatchDeviceFields(d.deviceFields, d.deviceInfo,
		d.collectInterval*1000)
	return cleanups, err
}

func (d *WatchList) DeviceGroups() []dcgm.GroupHandle {
	return d.deviceGroups
}

func (d *WatchList) DeviceFieldGroup() dcgm.FieldHandle {
	return d.deviceFieldGroup
}

type WatchListManager struct {
	entityWatchLists map[dcgm.Field_Entity_Group]WatchList
	counters         counters.CounterList
	gOpts            appconfig.DeviceOptions
	sOpts            appconfig.DeviceOptions
	cOpts            appconfig.DeviceOptions
	useFakeGPUs      bool
}

func NewWatchListManager(
	counters counters.CounterList, config *appconfig.Config,
) *WatchListManager {
	return &WatchListManager{
		entityWatchLists: make(map[dcgm.Field_Entity_Group]WatchList),
		counters:         counters,
		gOpts:            config.GPUDeviceOptions,
		sOpts:            config.SwitchDeviceOptions,
		cOpts:            config.CPUDeviceOptions,
		useFakeGPUs:      config.UseFakeGPUs,
	}
}

func (e *WatchListManager) CreateEntityWatchList(
	entityType dcgm.Field_Entity_Group, watcher devicewatcher.Watcher, collectInterval int64,
) error {
	deviceFields := watcher.GetDeviceFields(e.counters, entityType)

	labelDeviceFields := watcher.GetDeviceFields(e.counters.LabelCounters(), entityType)

	deviceInfo, err := deviceinfo.Initialize(e.gOpts, e.sOpts, e.cOpts, e.useFakeGPUs, entityType)
	if err != nil {
		return err
	}

	e.entityWatchLists[entityType] = *NewWatchList(
		deviceInfo,
		deviceFields,
		labelDeviceFields,
		watcher,
		collectInterval)

	return err
}

func (e *WatchListManager) EntityWatchList(deviceType dcgm.Field_Entity_Group) (WatchList, bool) {
	entityWatchList, exists := e.entityWatchLists[deviceType]
	return entityWatchList, exists
}
