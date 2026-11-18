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
package utils

import (
	"bytes"
	"crypto/rand"
	"encoding/binary"
	"encoding/gob"
	"fmt"
	"regexp"
	"sync"
	"time"
)

var invalidLabelCharRE = regexp.MustCompile(`[^a-zA-Z0-9_]`)

func WaitWithTimeout(wg *sync.WaitGroup, timeout time.Duration) error {
	c := make(chan struct{})
	go func() {
		defer close(c)
		wg.Wait()
	}()
	select {
	case <-c:
		return nil
	case <-time.After(timeout):
		return fmt.Errorf("timeout waiting for WaitGroup")
	}
}

func RandUint64() (uint64, error) {
	var num uint64
	err := binary.Read(rand.Reader, binary.BigEndian, &num)
	if err != nil {
		return 0, fmt.Errorf("failed to generate random 64-bit number; err: %w", err)
	}

	return num, nil
}

func DeepCopy[T any](src T) (dst T, err error) {
	var buf bytes.Buffer

	defer func() {
		if r := recover(); r != nil {

			dst = *new(T)
			err = fmt.Errorf("panic occurred: %v", r)
		}
	}()

	err = gob.NewEncoder(&buf).Encode(src)
	if err != nil {
		return *new(T), err
	}

	err = gob.NewDecoder(&buf).Decode(&dst)
	if err != nil {
		return *new(T), err
	}

	return dst, nil
}

func CleanupOnError(cleanups []func()) []func() {
	for _, cleanup := range cleanups {
		cleanup()
	}

	return nil
}

func SanitizeLabelName(s string) string {
	return invalidLabelCharRE.ReplaceAllString(s, "_")
}
