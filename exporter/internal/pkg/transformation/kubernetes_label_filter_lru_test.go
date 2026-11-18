/*
 * Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
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
	"fmt"
	"testing"

	"github.com/stretchr/testify/assert"

	"gpu-exporter/internal/pkg/appconfig"
)

func TestLabelFilterCache_LRUEviction(t *testing.T) {
	patterns := []string{"^label-.*"}
	cacheSize := 5

	podMapper := &PodMapper{
		Config: &appconfig.Config{
			KubernetesPodLabelAllowlistRegex: patterns,
		},
		labelFilterCache: newLabelFilterCache(patterns, cacheSize),
	}

	cache := podMapper.labelFilterCache

	for i := 1; i <= cacheSize; i++ {
		labelKey := fmt.Sprintf("label-%d", i)
		result := podMapper.shouldIncludeLabel(labelKey)
		assert.True(t, result, "Label should match pattern")
	}

	cache.mu.Lock()
	assert.Equal(t, cacheSize, len(cache.cache), "Cache should be at capacity")
	assert.Equal(t, cacheSize, cache.lruList.Len(), "LRU list should match cache size")
	cache.mu.Unlock()

	podMapper.shouldIncludeLabel("label-3")

	result := podMapper.shouldIncludeLabel("label-6")
	assert.True(t, result, "New label should match pattern")

	cache.mu.Lock()
	assert.Equal(t, cacheSize, len(cache.cache), "Cache should still be at capacity")
	assert.Equal(t, cacheSize, cache.lruList.Len(), "LRU list should still match cache size")

	_, exists := cache.cache["label-1"]
	assert.False(t, exists, "Oldest entry (label-1) should have been evicted")

	_, exists = cache.cache["label-3"]
	assert.True(t, exists, "Recently accessed entry (label-3) should still be in cache")

	_, exists = cache.cache["label-6"]
	assert.True(t, exists, "Newly added entry (label-6) should be in cache")
	cache.mu.Unlock()
}

func TestLabelFilterCache_LRUOrdering(t *testing.T) {
	patterns := []string{"^app$", "^tier$", "^env$"}
	cacheSize := 3

	podMapper := &PodMapper{
		Config: &appconfig.Config{
			KubernetesPodLabelAllowlistRegex: patterns,
		},
		labelFilterCache: newLabelFilterCache(patterns, cacheSize),
	}

	cache := podMapper.labelFilterCache

	podMapper.shouldIncludeLabel("app")
	podMapper.shouldIncludeLabel("tier")
	podMapper.shouldIncludeLabel("env")

	cache.mu.Lock()
	assert.Equal(t, cacheSize, len(cache.cache), "Cache should be at capacity")

	front := cache.lruList.Front()
	assert.Equal(t, "env", front.Value.(*labelCacheEntry).key, "Front should be most recent (env)")

	back := cache.lruList.Back()
	assert.Equal(t, "app", back.Value.(*labelCacheEntry).key, "Back should be oldest (app)")
	cache.mu.Unlock()

	podMapper.shouldIncludeLabel("app")

	cache.mu.Lock()
	front = cache.lruList.Front()
	assert.Equal(t, "app", front.Value.(*labelCacheEntry).key, "Front should now be app")

	back = cache.lruList.Back()
	assert.Equal(t, "tier", back.Value.(*labelCacheEntry).key, "Back should now be tier")
	cache.mu.Unlock()

	podMapper.shouldIncludeLabel("version")

	cache.mu.Lock()
	_, tierExists := cache.cache["tier"]
	assert.False(t, tierExists, "tier should have been evicted")

	_, versionExists := cache.cache["version"]
	assert.True(t, versionExists, "version should be in cache")

	_, appExists := cache.cache["app"]
	assert.True(t, appExists, "app should still be in cache")

	_, envExists := cache.cache["env"]
	assert.True(t, envExists, "env should still be in cache")
	cache.mu.Unlock()
}

func TestLabelFilterCache_ConcurrentAccess(t *testing.T) {
	patterns := []string{"^label-.*"}
	cacheSize := 100

	podMapper := &PodMapper{
		Config: &appconfig.Config{
			KubernetesPodLabelAllowlistRegex: patterns,
		},
		labelFilterCache: newLabelFilterCache(patterns, cacheSize),
	}

	const numGoroutines = 10
	const numOperationsPerGoroutine = 100

	done := make(chan bool)

	for g := 0; g < numGoroutines; g++ {
		go func(goroutineID int) {
			for i := 0; i < numOperationsPerGoroutine; i++ {
				labelKey := fmt.Sprintf("label-%d-%d", goroutineID, i)
				podMapper.shouldIncludeLabel(labelKey)
			}
			done <- true
		}(g)
	}

	for g := 0; g < numGoroutines; g++ {
		<-done
	}

	cache := podMapper.labelFilterCache
	cache.mu.Lock()
	assert.LessOrEqual(t, len(cache.cache), cacheSize, "Cache should not exceed max size")
	assert.LessOrEqual(t, cache.lruList.Len(), cacheSize, "LRU list should not exceed max size")
	assert.Equal(t, len(cache.cache), cache.lruList.Len(), "Cache map and list should be in sync")
	cache.mu.Unlock()
}
