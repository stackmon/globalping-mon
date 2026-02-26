#!/usr/bin/env python3

import argparse
import json
import time
import requests
import csv
import socket
import datetime
from collections import defaultdict
from typing import Dict, Any, Tuple, List

from prometheus_client import start_http_server, Gauge

API_BASE = "https://api.globalping.io/v1"


# ============================================================
# Prometheus Metrics (HTTP endpoint mode)
# ============================================================

PROM_METRICS = {
    "ping_avg": Gauge(
        "globalping_ping_avg_ms",
        "Average ping latency in ms",
        ["target", "country"]
    ),
    "http_avg": Gauge(
        "globalping_http_total_avg_ms",
        "Average HTTP total time in ms",
        ["target", "country"]
    ),
    "ping_avg_hop": Gauge(
        "globalping_ping_avg_hop_ms",
        "Average ping latency per hop",
        ["target", "country", "hop"]
    ),
    "http_avg_hop": Gauge(
        "globalping_http_total_avg_hop_ms",
        "Average HTTP total time per hop",
        ["target", "country", "hop"]
    ),
}


# ============================================================
# Utilities
# ============================================================

def load_config(path: str) -> Dict[str, Any]:
    with open(path, "r") as f:
        return json.load(f)


def build_locations(country_config: List[Dict[str, int]]) -> List[Dict[str, Any]]:
    locations = []
    for entry in country_config:
        for country, limit in entry.items():
            locations.append({
                "country": country,
                "limit": limit
            })
    return locations


def get_probe_identity(probe: Dict[str, Any]) -> Tuple:
    return (
        probe.get("country"),
        probe.get("region"),
        probe.get("city"),
        probe.get("asn"),
        probe.get("network"),
    )


# ============================================================
# API Calls
# ============================================================

def create_measurement(payload: Dict[str, Any], token: str = None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    r = requests.post(f"{API_BASE}/measurements", headers=headers, json=payload)
    r.raise_for_status()
    return r.json()


def get_results(measurement_id: str, token: str = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    while True:
        r = requests.get(f"{API_BASE}/measurements/{measurement_id}", headers=headers)
        r.raise_for_status()
        data = r.json()
        if data.get("status") == "finished":
            return data
        time.sleep(3)


def get_limits(token: str = None):
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    r = requests.get(f"{API_BASE}/limits", headers=headers)
    r.raise_for_status()
    return r.json()


# ============================================================
# Traceroute
# ============================================================

def analyze_traceroute(results: Dict, hop_aliases: Dict[str, str]):
    ip_to_alias = {ip: name for name, ip in hop_aliases.items()}
    matched = {}

    print("\n=== Traceroute Analysis ===")

    for r in results.get("results", []):
        probe = r.get("probe", {})
        identity = get_probe_identity(probe)
        hops = r.get("result", {}).get("hops", [])
        print(f"{probe.get('country')} {probe.get('city')} ASN{probe.get('asn')}")

        matched_aliases = []
        for hop in hops:
            ip = hop.get("resolvedAddress")
            if ip in ip_to_alias:
                matched_aliases.append(ip_to_alias[ip])

        if matched_aliases:
            matched[identity] = {
                "aliases": sorted(set(matched_aliases)),
                "probe": probe
            }

            print(
                f"{probe.get('country')} {probe.get('city')} ASN{probe.get('asn')} "
                f"→ matched hops {matched_aliases}"
            )

    return matched


# ============================================================
# Ping / HTTP Processing
# ============================================================

def process_ping(results, matched, country_summary, country_hop_summary):
    print("\n=== PING Results ===")

    for r in results.get("results", []):
        probe = r.get("probe", {})
        identity = get_probe_identity(probe)
        stats = r.get("result", {}).get("stats", {})
        country = probe.get("country")
        avg = stats.get("avg")

        if avg is None:
            continue

        country_summary[country]["ping_count"] += 1
        country_summary[country]["ping_avg"].append(avg)

        if identity in matched:
            for alias in matched[identity]["aliases"]:
                key = (country, alias)
                country_hop_summary[key]["ping_count"] += 1
                country_hop_summary[key]["ping_avg"].append(avg)

            print(
                f"{country}/{probe.get('city')} via {matched[identity]['aliases']} "
                f"avg={avg}ms loss={stats.get('loss')}%"
            )


def process_http(results, matched, country_summary, country_hop_summary):
    print("\n=== HTTP Results ===")

    for r in results.get("results", []):
        probe = r.get("probe", {})
        identity = get_probe_identity(probe)
        timings = r.get("result", {}).get("timings", {})
        country = probe.get("country")
        total = timings.get("total")

        if total is None:
            print(f"{probe.get('city')} skipped as total is missing")
            continue

        country_summary[country]["http_count"] += 1
        country_summary[country]["http_total"].append(total)

        if identity in matched:
            for alias in matched[identity]["aliases"]:
                key = (country, alias)
                country_hop_summary[key]["http_count"] += 1
                country_hop_summary[key]["http_total"].append(total)

            print(
                f"{country}/{probe.get('city')} via {matched[identity]['aliases']} "
                f"total={total}ms"
            )


# ============================================================
# Console Summary
# ============================================================

def print_summary(target, country_summary, country_hop_summary, traceroute_enabled):

    print("\n==================================================")
    print(f"SUMMARY FOR TARGET: {target}")
    print("==================================================")

    print("\n--- Country Summary ---")

    for country, stats in country_summary.items():
        print(f"\nCountry: {country}")

        if stats["ping_avg"] and stats["ping_count"]:
            avg = sum(stats["ping_avg"]) / len(stats["ping_avg"])
            print(f"  Ping probes: {stats['ping_count']}")
            print(f"  Ping avg: {avg:.3f} ms")

        if stats["http_total"] and stats["http_count"]:
            avg = sum(stats["http_total"]) / len(stats["http_total"])
            print(f"  HTTP probes: {stats['http_count']}")
            print(f"  HTTP avg: {avg:.3f} ms")


    if traceroute_enabled and country_hop_summary:
        print("\n--- Country + Hop Summary ---")

        for (country, hop), stats in country_hop_summary.items():
            print(f"\nCountry: {country} via {hop}")

            if stats["ping_avg"]:
                avg = sum(stats["ping_avg"]) / len(stats["ping_avg"])
                print(f"  Ping avg: {avg:.3f} ms")

            if stats["http_total"]:
                avg = sum(stats["http_total"]) / len(stats["http_total"])
                print(f"  HTTP avg: {avg:.3f} ms")


# ============================================================
# Exporters
# ============================================================

def export_json(results, path):
    with open(path, "w") as f:
        json.dump(results, f, indent=2)


def export_csv(results, path):
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["target", "country", "hop", "ping_avg", "http_avg"])

        for target, data in results["targets"].items():

            for country, stats in data["country_summary"].items():
                ping_avg = (
                    sum(stats["ping_avg"]) / len(stats["ping_avg"])
                    if stats["ping_avg"] else ""
                )
                http_avg = (
                    sum(stats["http_total"]) / len(stats["http_total"])
                    if stats["http_total"] else ""
                )
                writer.writerow([target, country, "", ping_avg, http_avg])

            for (country, hop), stats in data["country_hop_summary"].items():
                ping_avg = (
                    sum(stats["ping_avg"]) / len(stats["ping_avg"])
                    if stats["ping_avg"] else ""
                )
                http_avg = (
                    sum(stats["http_total"]) / len(stats["http_total"])
                    if stats["http_total"] else ""
                )
                writer.writerow([target, country, hop, ping_avg, http_avg])


def export_prometheus_textfile(results, path):
    lines = []

    for target, data in results["targets"].items():
        for country, stats in data["country_summary"].items():

            if stats["ping_avg"]:
                avg = sum(stats["ping_avg"]) / len(stats["ping_avg"])
                lines.append(
                    f'globalping_ping_avg_ms{{target="{target}",country="{country}"}} {avg}'
                )

            if stats["http_total"]:
                avg = sum(stats["http_total"]) / len(stats["http_total"])
                lines.append(
                    f'globalping_http_total_avg_ms{{target="{target}",country="{country}"}} {avg}'
                )

    with open(path, "w") as f:
        f.write("\n".join(lines))


def export_statsd(results, destination):
    host, port = destination.split(":")
    port = int(port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    for target, data in results["targets"].items():
        for country, stats in data["country_summary"].items():

            if stats["ping_avg"]:
                avg = sum(stats["ping_avg"]) / len(stats["ping_avg"])
                metric = f"globalping.{target}.{country}.ping_avg:{avg}|g"
                sock.sendto(metric.encode(), (host, port))

            if stats["http_total"]:
                avg = sum(stats["http_total"]) / len(stats["http_total"])
                metric = f"globalping.{target}.{country}.http_avg:{avg}|g"
                sock.sendto(metric.encode(), (host, port))

    sock.close()


# ============================================================
# Prometheus HTTP Update
# ============================================================

def update_prometheus_metrics(all_results):

    for target, data in all_results["targets"].items():

        for country, stats in data["country_summary"].items():

            if stats["ping_avg"]:
                avg = sum(stats["ping_avg"]) / len(stats["ping_avg"])
                PROM_METRICS["ping_avg"].labels(target, country).set(avg)

            if stats["http_total"]:
                avg = sum(stats["http_total"]) / len(stats["http_total"])
                PROM_METRICS["http_avg"].labels(target, country).set(avg)


# ============================================================
# ASN relation from Traceroute
# ============================================================

def build_asn_locations_from_traceroute(traceroute_results):
    """
    Build follow-up ASN-based locations from traceroute results.

    This version preserves duplicates so that:
    - If multiple traceroute probes come from same country+ASN,
      the same number of ping/http probes will be created.
    """

    locations = []

    for r in traceroute_results.get("results", []):
        probe = r.get("probe", {})
        country = probe.get("country")
        asn = probe.get("asn")

        if country and asn:
            locations.append({
                "country": country,
                "asn": asn
            })

    return locations


# ============================================================
# Measurement Engine
# ============================================================

def run_measurements(config, args):

    traceroute_enabled = config.get("traceroute_enabled", True)
    ping_enabled = config.get("ping_enabled", True)
    http_enabled = config.get("http_enabled", True)

    base_locations = build_locations(config["countries"])
    hop_aliases = config.get("check_hops", {})

    all_results = {"targets": {}}

    for target in config["targets"]:

        print(f"\n==============================")
        print(f"Processing target: {target}")
        print("==============================")

        country_summary = defaultdict(lambda: {
            "ping_count": 0,
            "ping_avg": [],
            "http_count": 0,
            "http_total": []
        })

        country_hop_summary = defaultdict(lambda: {
            "ping_count": 0,
            "ping_avg": [],
            "http_count": 0,
            "http_total": []
        })

        matched = {}
        followup_locations = base_locations

        # =====================================================
        # TRACEROUTE PHASE
        # =====================================================
        if traceroute_enabled:

            traceroute_payload = {
                "type": "traceroute",
                "target": target,
                "locations": base_locations,
                "measurementOptions": {
                    "port": config.get("port", 443),
                    "protocol": config.get("traceroute_protocol", "TCP")
                }
            }
            traceroute = create_measurement(traceroute_payload, args.token)
            traceroute_results = get_results(traceroute["id"], args.token)

            matched = analyze_traceroute(traceroute_results, hop_aliases)

            # 🔥 NEW: Build ASN-based follow-up locations
            followup_locations = build_asn_locations_from_traceroute(
                traceroute_results
            )

            print("\nASN follow-up locations:")
            for loc in followup_locations:
                print(f"  {loc}")

        # =====================================================
        # PING PHASE
        # =====================================================
        if ping_enabled:

            ping_locations = (
                followup_locations
                if traceroute_enabled
                else base_locations
            )

            ping_payload = {
                "type": "ping",
                "target": target,
                "locations": ping_locations,
                "measurementOptions": {
                    "port": config.get("port", 443),
                    "protocol": config.get("ping_protocol", "ICMP")
                }
            }

            ping = create_measurement(ping_payload, args.token)
            ping_results = get_results(ping["id"], args.token)

            process_ping(
                ping_results,
                matched if traceroute_enabled else {},
                country_summary,
                country_hop_summary
            )

        # =====================================================
        # HTTP PHASE
        # =====================================================
        if http_enabled:

            http_locations = (
                followup_locations
                if traceroute_enabled
                else base_locations
            )

            http_payload = {
                "type": "http",
                "target": target,
                "locations": http_locations,
                "measurementOptions": {
                    "port": config.get("port", 443),
                    "request": {
                        "method": config.get("method", "GET")
                    }
                }
            }

            if config.get("http_protocol"):
                http_payload["measurementOptions"]["protocol"] = config["http_protocol"]

            http = create_measurement(http_payload, args.token)
            http_results = get_results(http["id"], args.token)

            process_http(
                http_results,
                matched if traceroute_enabled else {},
                country_summary,
                country_hop_summary
            )

        # =====================================================
        # SUMMARY
        # =====================================================
        print_summary(
            target,
            country_summary,
            country_hop_summary,
            traceroute_enabled
        )

        all_results["targets"][target] = {
            "country_summary": dict(country_summary),
            "country_hop_summary": dict(country_hop_summary)
        }

    return all_results


# ============================================================
# Limits
# ============================================================

def print_limits(token=None):
    limits_data = get_limits(token)
    create_limits = limits_data["rateLimit"]["measurements"]["create"]

    print("\n=== API Rate Limits ===")
    print(f"Limit: {create_limits['limit']}")
    print(f"Remaining: {create_limits['remaining']}")
    print(f"Reset in: {datetime.timedelta(seconds=create_limits['reset'])}")


# ============================================================
# Main
# ============================================================

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--token")
    parser.add_argument("--json-output")
    parser.add_argument("--csv-output")
    parser.add_argument("--prometheus-output")
    parser.add_argument("--statsd-output")
    parser.add_argument("--prometheus-http", action="store_true")
    parser.add_argument("--listen", default="0.0.0.0:9105")
    parser.add_argument("--interval", type=int, default=300)

    args = parser.parse_args()
    config = load_config(args.config)

    if args.prometheus_http:

        host, port = args.listen.split(":")
        port = int(port)

        print(f"Starting Prometheus HTTP server on {host}:{port}")
        start_http_server(port, addr=host)

        while True:
            results = run_measurements(config, args)
            update_prometheus_metrics(results)
            time.sleep(args.interval)

    else:
        results = run_measurements(config, args)

        if args.json_output:
            export_json(results, args.json_output)

        if args.csv_output:
            export_csv(results, args.csv_output)

        if args.prometheus_output:
            export_prometheus_textfile(results, args.prometheus_output)

        if args.statsd_output:
            export_statsd(results, args.statsd_output)

        print_limits(args.token)


if __name__ == "__main__":
    main()

