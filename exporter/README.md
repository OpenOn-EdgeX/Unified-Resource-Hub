# GPU Exporter

A Prometheus exporter for NVIDIA GPUs, based on NVIDIA DCGM Exporter. It collects a fresh payload per scrape. See [NOTICE](NOTICE) for attribution.

From this directory on Linux, with Go 1.24.5 and a C compiler:

```sh
CGO_ENABLED=1 go build -mod=readonly -trimpath -o gpu-exporter ./cmd/gpu-exporter
CGO_ENABLED=1 go test -mod=readonly ./...
./gpu-exporter --address=127.0.0.1:9400 --collectors=etc/default-counters.csv
```

Running the exporter requires a supported NVIDIA GPU, driver and DCGM runtime. `/health` reports service health; `/metrics` serves metrics. Enable access from other hosts only through a trusted network or authenticated proxy.
