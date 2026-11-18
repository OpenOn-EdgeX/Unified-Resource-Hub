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
package stdout

import (
	"strings"
	"time"
)

type outputEntry struct {
	Timestamp   time.Time
	Level       string
	Message     string
	IsRawString bool
}

func parseOutputEntry(entry string) outputEntry {

	fields := strings.Fields(entry)

	if len(fields) > 2 {

		timestamp, err := time.Parse("2006-01-02 15:04:05.000", fields[0]+" "+fields[1])
		if err != nil {
			return outputEntry{
				Message:     entry,
				IsRawString: true,
			}
		}

		level := fields[2]

		remainder := strings.Join(fields[4:], " ")

		return outputEntry{
			Timestamp: timestamp,
			Level:     level,
			Message:   remainder,
		}
	}

	return outputEntry{
		Message:     entry,
		IsRawString: true,
	}
}
