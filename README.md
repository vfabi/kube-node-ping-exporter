# kube-node-ping-exporter

Simple application to send ICMP echo requests that exposes results as Prometheus metrics. It helps to measure latency from or between Kubernetes nodes.  
It deploys as DaemonSet to every Kubernetes node, get remote IP addresses list for ICMP checks from ConfigMap and expose ICMP requests results as Prometheus metrics.  
Can be used to send ICMP requests between Kubernetes nodes itself or against remote IP addresses.

## Features

- Sends ICMP echo requests to remote hosts and expose results as Prometheus metrics

## Alternatives

- https://github.com/simonswine/kube-latency
- https://github.com/czerwonk/ping_exporter
- https://github.com/bloomberg/goldpinger

## Technology stack

- Python 3.6+ + prometheus-client

## Requirements and dependencies

Python requirements in `app/requirements.txt`

## Configuration

- Put remote IP addresses list for ICMP checks into `kube-node-ping-exporter` ConfigMap `nodes.json` section. Example configuration located in `deploy/main.yaml`.
- Update `deploy/main.yaml` if necessary.

## Deploy

Just use `deploy/main.yaml` example configuration to deploy into Kubernetes.  
It deploys `kube-node-ping-exporter` to every Kubernetes node as DaemonSet and takes IP address list for ICMP checks from `kube-node-ping-exporter` ConfigMap `nodes.json` section.

## Usage

1. Configure and deploy `kube-node-ping-exporter`.
2. Configure your Prometheus to scrape metrics from `kube-node-ping-exporter` pods. Prometheus configuration example:
```
- job_name: 'kube-node-ping-exporter'
    kubernetes_sd_configs:
    - role: pod
    relabel_configs:
    - source_labels: [__meta_kubernetes_namespace]
        action: replace
        target_label: namespace
    - source_labels: [__meta_kubernetes_pod_name]
        action: replace
        target_label: pod
    - source_labels: [__address__]
        action: replace
        regex: ([^:]+)(?::\d+)?
        replacement: ${1}:8000
        target_label: __address__
    - source_labels: [__meta_kubernetes_pod_label_app_kubernetes_io_name]
        action: keep
        regex: 'kube-node-ping-exporter'
```

##  Docker

[![Generic badge](https://img.shields.io/badge/hub.docker.com-vfabi/kube_node_ping_exporter-<>.svg)](https://hub.docker.com/repository/docker/vfabi/kube-node-ping-exporter)

## Build

```
docker buildx build --push --platform=linux/amd64,linux/arm64 -t vfabi/kube-node-ping-exporter:latest -f Dockerfile .
```

## Contributing

Please refer to each project's style and contribution guidelines for submitting patches and additions. In general, we follow the "fork-and-pull" Git workflow.

 1. **Fork** the repo on GitHub
 2. **Clone** the project to your own machine
 3. **Commit** changes to your own branch
 4. **Push** your work back up to your fork
 5. Submit a **Pull request** so that we can review your changes

NOTE: Be sure to merge the latest from "upstream" before making a pull request!

## License

Apache 2.0
