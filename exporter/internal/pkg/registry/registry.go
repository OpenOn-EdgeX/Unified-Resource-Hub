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
package registry

import (
	"sync"
	"sync/atomic"

	"github.com/NVIDIA/go-dcgm/pkg/dcgm"

	"golang.org/x/sync/errgroup"

	"gpu-exporter/internal/pkg/collector"
	"gpu-exporter/internal/pkg/counters"
)

type groupCounterTuple struct {
	Group   dcgm.Field_Entity_Group
	Counter counters.Counter
}

type Registry struct {
	collectorGroups     map[dcgm.Field_Entity_Group][]collector.Collector
	collectorGroupsSeen map[collector.EntityCollectorTuple]struct{}
	mtx                 sync.RWMutex
	lastCollectMeta     atomic.Value
}

func NewRegistry() *Registry {
	return &Registry{
		collectorGroups:     map[dcgm.Field_Entity_Group][]collector.Collector{},
		collectorGroupsSeen: map[collector.EntityCollectorTuple]struct{}{},
	}
}

func (r *Registry) Register(entityCollectorTuples collector.EntityCollectorTuple) {
	if _, exists := r.collectorGroupsSeen[entityCollectorTuples]; exists {
		return
	}
	r.collectorGroups[entityCollectorTuples.Entity()] = append(r.collectorGroups[entityCollectorTuples.Entity()],
		entityCollectorTuples.Collector())
	r.collectorGroupsSeen[entityCollectorTuples] = struct{}{}
}

func (r *Registry) Gather() (MetricsByCounterGroup, error) {
	r.mtx.Lock()
	defer r.mtx.Unlock()

	var wg sync.WaitGroup

	g := new(errgroup.Group)

	var sm sync.Map

	for group, collectors := range r.collectorGroups {
		for _, c := range collectors {
			c := c
			group := group
			wg.Add(1)
			g.Go(func() error {
				metrics, err := c.GetMetrics()
				if err != nil {
					return err
				}

				if mp, ok := c.(collector.MetaProvider); ok {
					if meta := mp.GetCollectMeta(); meta != nil {
						r.SetCollectMeta(meta)
					}
				}

				for counter, metricVals := range metrics {
					val, _ := sm.LoadOrStore(groupCounterTuple{Group: group, Counter: counter}, []collector.Metric{})
					out := val.([]collector.Metric)
					out = append(out, metricVals...)
					sm.Store(groupCounterTuple{Group: group, Counter: counter}, out)
				}

				return nil
			})
		}
	}

	if err := g.Wait(); err != nil {
		return nil, err
	}

	output := MetricsByCounterGroup{}

	sm.Range(func(key, value interface{}) bool {
		tuple := key.(groupCounterTuple)
		if _, exists := output[tuple.Group]; !exists {
			output[tuple.Group] = map[counters.Counter][]collector.Metric{}
		}
		output[tuple.Group][tuple.Counter] = value.([]collector.Metric)
		return true
	})

	return output, nil
}

func (r *Registry) Cleanup() {
	for _, collectors := range r.collectorGroups {
		for _, c := range collectors {
			c.Cleanup()
		}
	}
}

func (r *Registry) SetCollectMeta(m *collector.CollectMeta) {
	r.lastCollectMeta.Store(m)
}

func (r *Registry) GetCollectMeta() *collector.CollectMeta {
	if v := r.lastCollectMeta.Load(); v != nil {
		return v.(*collector.CollectMeta)
	}
	return nil
}
