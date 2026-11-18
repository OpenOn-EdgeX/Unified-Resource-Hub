/*
 * Copyright (c) 2025, NVIDIA CORPORATION.  All rights reserved.
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
package capabilities

import (
	"fmt"
	"log/slog"
	"os"
	"strconv"
	"strings"
	"syscall"
)

const (
	CAP_SYS_ADMIN = 21
)

func HasCapability(cap int) (bool, error) {

	if cap < 0 || cap > 63 {
		return false, fmt.Errorf("invalid capability number: %d (must be 0-63)", cap)
	}

	data, err := os.ReadFile("/proc/self/status")
	if err != nil {
		return false, fmt.Errorf("failed to read /proc/self/status: %w", err)
	}

	for line := range strings.SplitSeq(string(data), "\n") {
		if strings.HasPrefix(line, "CapEff:") {

			fields := strings.Fields(line)
			if len(fields) < 2 {
				continue
			}

			capHex := fields[1]
			capMask, err := strconv.ParseUint(capHex, 16, 64)
			if err != nil {
				return false, fmt.Errorf("failed to parse capability mask: %w", err)
			}

			return (capMask & (1 << uint(cap))) != 0, nil
		}
	}

	return false, fmt.Errorf("could not find CapEff in /proc/self/status")
}

func CheckSysAdmin() bool {
	has, err := HasCapability(CAP_SYS_ADMIN)
	if err != nil {
		slog.Warn("Failed to check for CAP_SYS_ADMIN capability",
			slog.String("error", err.Error()))
		return false
	}
	return has
}

func WarnIfMissingProfilingCapabilities(hasProfilingMetrics bool) {
	if !hasProfilingMetrics {

		return
	}

	if CheckSysAdmin() {

		return
	}

	slog.Warn("dcgm-exporter doesn't have sufficient privileges to expose profiling metrics. To get profiling metrics with dcgm-exporter, use --cap-add SYS_ADMIN")
}

func GetCurrentCapabilities() string {
	data, err := os.ReadFile("/proc/self/status")
	if err != nil {
		return fmt.Sprintf("error reading capabilities: %v", err)
	}

	for line := range strings.SplitSeq(string(data), "\n") {
		if strings.HasPrefix(line, "CapEff:") {
			fields := strings.Fields(line)
			if len(fields) >= 2 {
				capHex := fields[1]
				capMask, err := strconv.ParseUint(capHex, 16, 64)
				if err != nil {
					return fmt.Sprintf("error parsing: %v", err)
				}

				caps := []string{}
				capNames := map[int]string{
					0:  "CAP_CHOWN",
					1:  "CAP_DAC_OVERRIDE",
					2:  "CAP_DAC_READ_SEARCH",
					3:  "CAP_FOWNER",
					4:  "CAP_FSETID",
					5:  "CAP_KILL",
					6:  "CAP_SETGID",
					7:  "CAP_SETUID",
					8:  "CAP_SETPCAP",
					9:  "CAP_LINUX_IMMUTABLE",
					10: "CAP_NET_BIND_SERVICE",
					11: "CAP_NET_BROADCAST",
					12: "CAP_NET_ADMIN",
					13: "CAP_NET_RAW",
					14: "CAP_IPC_LOCK",
					15: "CAP_IPC_OWNER",
					16: "CAP_SYS_MODULE",
					17: "CAP_SYS_RAWIO",
					18: "CAP_SYS_CHROOT",
					19: "CAP_SYS_PTRACE",
					20: "CAP_SYS_PACCT",
					21: "CAP_SYS_ADMIN",
					22: "CAP_SYS_BOOT",
					23: "CAP_SYS_NICE",
					24: "CAP_SYS_RESOURCE",
					25: "CAP_SYS_TIME",
					26: "CAP_SYS_TTY_CONFIG",
				}

				for cap := 0; cap < 64; cap++ {

					if (capMask & (1 << uint(cap))) != 0 {
						if name, ok := capNames[cap]; ok {
							caps = append(caps, name)
						} else {
							caps = append(caps, fmt.Sprintf("CAP_%d", cap))
						}
					}
				}

				if len(caps) == 0 {
					return "no capabilities"
				}
				return strings.Join(caps, ", ")
			}
		}
	}

	return "unknown"
}

func DropAllCapabilitiesExcept(keep []int) error {

	slog.Debug("Capability dropping is handled by container runtime",
		slog.String("method", "securityContext.capabilities.drop"))
	return nil
}

func LogCapabilityInfo() {
	uid := os.Getuid()
	euid := os.Geteuid()
	gid := os.Getgid()
	egid := os.Getegid()

	caps := GetCurrentCapabilities()

	slog.Debug("Process capability information",
		slog.Int("uid", uid),
		slog.Int("euid", euid),
		slog.Int("gid", gid),
		slog.Int("egid", egid),
		slog.String("capabilities", caps),
		slog.Bool("has_cap_sys_admin", CheckSysAdmin()))
}

func IsRunningAsRoot() bool {
	return syscall.Geteuid() == 0
}
