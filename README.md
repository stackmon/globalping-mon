# Globaping IO Measurement Script

Network measurement automation built on top of the Globalping API (https://globalping.io/).

This script performs:

-   Traceroute measurements
-   HTTP measurements
-   Country-level summaries
-   ASN-based follow-up measurements (derived from traceroute results)
-   Export to JSON, CSV, Prometheus, or StatsD
-   Optional Prometheus HTTP exporter mode

------------------------------------------------------------------------

# Overview

The script:

1.  Runs traceroute from selected countries.
2.  Extracts ASN information from traceroute probes.
3.  Uses discovered ASN locations for follow-up measurements.
4.  Runs HTTP (and optionally ping) tests.
5.  Aggregates results:
    -   Per country
    -   Per country + matched hop alias
6.  Exports metrics or exposes them for monitoring systems.

------------------------------------------------------------------------

# Example config.json

``` json
{
  "targets": [
    "docs.example.com",
    "console.example.com"
  ],
  "port": 443,
  "traceroute_enabled": true,
  "ping_enabled": false,
  "http_enabled": true,
  "traceroute_protocol": "TCP",
  "ping_protocol": "ICMP",
  "http_protocol": "HTTPS",
  "method": "GET",
  "countries": [
    {"DE": 10},
    {"IT": 8},
    {"ES": 5}
  ],
  "check_hops": {
    "internet_line1": "1.2.3.4",
    "internet_line2": "5.6.7.8"
  }
}
```

------------------------------------------------------------------------

# Configuration Reference

## targets

List of domains to measure.

## port

Port used for traceroute, ping, and HTTP measurements.

## traceroute_enabled

Enable/disable traceroute phase.

## ping_enabled

Enable/disable ping phase.

## http_enabled

Enable/disable HTTP phase.

## traceroute_protocol

Protocol used for traceroute (TCP / UDP / ICMP).

## ping_protocol

Protocol used for ping (ICMP / TCP).

## http_protocol

HTTP protocol (HTTP / HTTPS).

## method

HTTP method (GET / POST / HEAD).

## countries

Defines probe distribution per country.

Example:

``` json
[
  {"DE": 10},
  {"IT": 8},
  {"ES": 5}
]
```

## check_hops

Optional mapping of hop aliases to IP addresses. Used during traceroute
analysis to match specific network hops.

------------------------------------------------------------------------

# Installation

``` bash
pip install requests prometheus-client
```

------------------------------------------------------------------------

# Usage

## Basic Run

``` bash
python3 globaping.py --config config.json
```

## With API Token

``` bash
python3 globaping.py --config config.json --token YOUR_API_TOKEN
```

## Export to JSON

``` bash
python3 globaping.py --config config.json --json-output results.json
```

## Export to CSV

``` bash
python3 globaping.py --config config.json --csv-output results.csv
```

## Prometheus Textfile Export

``` bash
python3 globaping.py   --config config.json   --prometheus-output /var/lib/node_exporter/globalping.prom
```

## Prometheus HTTP Exporter Mode

``` bash
python3 globaping.py   --config config.json   --prometheus-http   --listen 0.0.0.0:9105   --interval 300
```

Metrics available at:

http://0.0.0.0:9105/metrics

------------------------------------------------------------------------

## StatsD Export

``` bash
python3 globaping.py   --config config.json   --statsd-output 127.0.0.1:8125
```

------------------------------------------------------------------------

# Execution Flow

Config → Traceroute → ASN Extraction\
    ↓\
  HTTP/Ping\
    ↓\
Aggregation\
    ↓\
Export (JSON / CSV / Prom / StatsD)

------------------------------------------------------------------------

# Rate Limits

After execution, API rate limits are printed:

-   Limit
-   Remaining
-   Reset time

------------------------------------------------------------------------

# Use Cases

-   Multi-country latency monitoring
-   ISP/ASN path validation
-   Routing comparison between providers
-   Prometheus-based SLO monitoring
-   External uptime and performance checks

------------------------------------------------------------------------

# Notes

-   If traceroute_enabled is true, follow-up measurements are ASN-based.
-   If disabled, measurements use country-based limits only.
-   Duplicated ASN probes are preserved intentionally to maintain probe
    distribution accuracy.
