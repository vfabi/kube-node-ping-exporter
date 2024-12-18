#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
    @project: node-ping-exporter
    @copyright: © 2022 by vfabi
    @author: vfabi
    @support: vfabi
    @initial date: 2022-12-03 21:48:07
    @license: this file is subject to the terms and conditions defined
        in file 'LICENSE.txt', which is part of this source code package
    @description:
    @todo:
"""

import os
import re
import time
import json
import subprocess
import statistics
from prometheus_client import CollectorRegistry, start_http_server, Counter, Gauge, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR


# PROMETHEUS_DISABLE_CREATED_SERIES = True  # Set this environment variable to disable auto creation of "*_created" metrics. More details at https://github.com/prometheus/client_python/blob/master/README.md#disabling-_created-metrics
APP_INTERNAL_LOOP_TIMEOUT_SEC = int(os.getenv('APP_INTERNAL_LOOP_TIMEOUT_SEC', 10))  # Application main loop timeout, a time between main() function runs.
APP_PORT = int(os.getenv('APP_PORT', 8000))  # Application port to scrape metrics from.
APP_NODE_NAME = os.getenv('APP_NODE_NAME', 'localhost')  # Node name where this application run.
APP_PINGS_COUNT = int(os.getenv('APP_PINGS_COUNT', 10))  # Number of ICMP requests send per one IP address.
APP_CONFIG_FILE = os.getenv('APP_CONFIG_FILE', '/app/nodes.json')  # Target IP addresses list file absolute path.

REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(REGISTRY._names_to_collectors['python_gc_objects_collected_total'])

FPING_CMDLINE = f"/usr/sbin/fping -4 -p 1000 -A -C {APP_PINGS_COUNT} -B 1 -q -r 1".split(" ")
FPING_REGEX = re.compile(r"^(\S*)\s*: (.*)$", re.MULTILINE)

registry = CollectorRegistry()
prometheus_exceptions_counter = Counter('kube_node_ping_exceptions', 'Total number of exceptions', [], registry=registry)
prom_metrics = {
    "sent": Counter(
        'kube_node_ping_packets_sent_total',
        'ICMP packets sent',
        [
            'destination_node',
            'destination_node_ip',
            'source_node'
        ],
        registry=registry
    ),
    "received": Counter(
        'kube_node_ping_packets_received_total',
        'ICMP packets received',
        [
            'destination_node',
            'destination_node_ip',
            'source_node'
        ],
        registry=registry
    ),
    "rtt": Counter(
        'kube_node_ping_rtt_milliseconds_total',
        'round-trip time',
        [
            'destination_node',
            'destination_node_ip',
            'source_node'
        ],
        registry=registry
    ),
    "min": Gauge(
        'kube_node_ping_rtt_min',
        'minimum round-trip time',
        [
            'destination_node',
            'destination_node_ip',
            'source_node'
        ],
        registry=registry
    ),
    "max": Gauge(
        'kube_node_ping_rtt_max',
        'maximum round-trip time',
        [
            'destination_node',
            'destination_node_ip',
            'source_node'
        ],
        registry=registry
    ),
    "mdev": Gauge(
        'kube_node_ping_rtt_mdev',
        'mean deviation of round-trip times',
        [
            'destination_node',
            'destination_node_ip',
            'source_node'
        ],
        registry=registry
    ),
    "mean": Gauge(
        'kube_node_ping_rtt_mean',
        'mean (average) of round-trip times',
        [
            'destination_node',
            'destination_node_ip',
            'source_node'
        ],
        registry=registry
    ),
    "median": Gauge(
        'kube_node_ping_rtt_median',
        'median (middle value) of round-trip times',
        [
            'destination_node',
            'destination_node_ip',
            'source_node'
        ],
        registry=registry
    )
}


# def validate_envs():
#     envs = {
#         "APP_NODE_NAME": os.getenv("APP_NODE_NAME")
#     }

#     for k, v in envs.items():
#         if not v:
#             raise ValueError("{} environment variable is empty.".format(k))
#     return envs


@prometheus_exceptions_counter.count_exceptions()
def compute_results(results):
    computed = {}

    matches = FPING_REGEX.finditer(results)
    for match in matches:
        ip = match.group(1)
        ping_results = match.group(2)
        if "duplicate" in ping_results:
            continue
        splitted = ping_results.split(" ")
        if len(splitted) != APP_PINGS_COUNT:
            raise ValueError("Ping returned wrong number of results: \"{}\"".format(splitted))

        positive_results = [float(x) for x in splitted if x != "-"]
        if len(positive_results) > 0:
            computed[ip] = {
                "sent": APP_PINGS_COUNT,
                "received": len(positive_results),
                "rtt": sum(positive_results),
                "max": max(positive_results),
                "min": min(positive_results),
                "mdev": statistics.pstdev(positive_results),
                "mean": round(statistics.mean(positive_results),2),
                "median": round(statistics.mean(positive_results),2)
            }
        else:
            computed[ip] = {
                "sent": APP_PINGS_COUNT,
                "received": len(positive_results),
                "rtt": 0,
                "max": 0,
                "min": 0,
                "mdev": 0,
                "mean": 0,
                "median": 0
            }

    if not len(computed):
        raise ValueError("Regex match\"{}\" found nothing in fping output \"{}\"".format(FPING_REGEX, results))
    return computed


@prometheus_exceptions_counter.count_exceptions()
def call_fping(ips):
    cmdline = FPING_CMDLINE + ips
    process = subprocess.run(
        cmdline,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True
    )

    if process.returncode == 3:
        raise ValueError("Invalid arguments: {}".format(cmdline))
    if process.returncode == 4:
        # print(f'cmdline: {cmdline}')
        # print(f'process.stdout: {process.stdout}')
        raise OSError("fping reported syscall error: {}".format(process.stderr))
    return process.stdout


def main():
    labeled_prom_metrics = []

    with open(APP_CONFIG_FILE, "r") as f:
        config = json.loads(f.read())

    if labeled_prom_metrics:
        for node in config:
            if (node["name"], node["ipAddress"]) not in [(metric["node_name"], metric["ip"]) for metric in labeled_prom_metrics]:
                for k, v in prom_metrics.items():
                    v.remove(node["name"], node["ipAddress"])

    # labeled_prom_metrics = []

    for node in config:
        if node["name"] != APP_NODE_NAME:
            metrics = {"node_name": node["name"], "ip": node["ipAddress"], "prom_metrics": {}}

            for k, v in prom_metrics.items():
                metrics["prom_metrics"][k] = v.labels(node["name"], node["ipAddress"], APP_NODE_NAME)

            labeled_prom_metrics.append(metrics)

    out = call_fping([prom_metric["ip"] for prom_metric in labeled_prom_metrics])
    computed = compute_results(out)

    for dimension in labeled_prom_metrics:
        # result = computed[dimension["ip"]]
        dimension["prom_metrics"]["sent"].inc(computed[dimension["ip"]]["sent"])  # kube_node_ping_packets_sent_total
        dimension["prom_metrics"]["received"].inc(computed[dimension["ip"]]["received"])  # kube_node_ping_packets_received_total
        dimension["prom_metrics"]["rtt"].inc(computed[dimension["ip"]]["rtt"])  # kube_node_ping_rtt_milliseconds_total
        dimension["prom_metrics"]["min"].set(computed[dimension["ip"]]["min"])  # kube_node_ping_rtt_min
        dimension["prom_metrics"]["max"].set(computed[dimension["ip"]]["max"])  # kube_node_ping_rtt_max
        dimension["prom_metrics"]["mdev"].set(computed[dimension["ip"]]["mdev"])  # kube_node_ping_rtt_mdev
        dimension["prom_metrics"]["mean"].set(computed[dimension["ip"]]["mean"])  # kube_node_ping_rtt_mean
        dimension["prom_metrics"]["median"].set(computed[dimension["ip"]]["median"])  # kube_node_ping_rtt_median


if __name__ == '__main__':
    start_http_server(APP_PORT, registry=registry)
    while True:
        time.sleep(APP_INTERNAL_LOOP_TIMEOUT_SEC)
        main()
