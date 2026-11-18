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
package transformation

import (
	"container/list"
	"context"
	"regexp"
	"sync"

	"k8s.io/client-go/informers"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/tools/cache"

	"gpu-exporter/internal/pkg/appconfig"
	"gpu-exporter/internal/pkg/collector"
	"gpu-exporter/internal/pkg/deviceinfo"
)

type Transform interface {
	Process(metrics collector.MetricsByCounter, deviceInfo deviceinfo.Provider) error
	Name() string
}

type PodMapper struct {
	Config               *appconfig.Config
	Client               kubernetes.Interface
	ResourceSliceManager *DRAResourceSliceManager
	labelFilterCache     *LabelFilterCache
}

type LabelFilterCache struct {
	compiledPatterns []*regexp.Regexp
	cache            map[string]*list.Element
	lruList          *list.List
	mu               sync.Mutex
	maxSize          int
	enabled          bool
}

type labelCacheEntry struct {
	key   string
	value bool
}

type PodInfo struct {
	Name             string
	Namespace        string
	Container        string
	UID              string
	VGPU             string
	Labels           map[string]string
	DynamicResources *DynamicResourceInfo
}

type DRAResourceSliceManager struct {
	factory       informers.SharedInformerFactory
	informer      cache.SharedIndexInformer
	cancelContext context.CancelFunc
	mu            sync.RWMutex
	deviceToUUID  map[string]string
	migDevices    map[string]*DRAMigDeviceInfo
}

type PodMetadata struct {
	UID    string
	Labels map[string]string
}

type DynamicResourceInfo struct {
	ClaimName      string
	ClaimNamespace string
	DriverName     string
	PoolName       string
	DeviceName     string

	MIGInfo *DRAMigDeviceInfo
}

type DRAMigDeviceInfo struct {
	MIGDeviceUUID string
	Profile       string
	ParentUUID    string
}
