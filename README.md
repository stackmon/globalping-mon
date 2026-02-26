# globalping-mon
Monitoring of sites using globalping.io

Globaping IO Measurement Script

Network measurement automation built on top of the Globalping API.

This script performs:

🌍 Traceroute measurements

🌐 HTTP measurements

📊 Country-level summaries

🔁 ASN-based follow-up measurements (derived from traceroute results)

📤 Export to JSON, CSV, Prometheus, or StatsD

📡 Optional Prometheus HTTP exporter mode

Overview

The script:

Runs traceroute from selected countries.

Extracts ASN information from traceroute probes.

Uses discovered ASN locations for follow-up measurements.

Runs HTTP (and optionally ping) tests.

Aggregates results:

Per country

Per country + matched hop alias

Exports metrics or exposes them for monitoring systems.

Features
Measurement Types

Traceroute (TCP by default)

HTTP (HTTPS + GET by default)

Optional Ping

Smart ASN Follow-up

After traceroute:

The script builds ASN-based probe locations.

Follow-up HTTP/Ping measurements run against the same ASN paths discovered.

This provides much more accurate network-path-specific monitoring.

Export Options

JSON

CSV

Prometheus textfile format

Prometheus HTTP endpoint

StatsD (UDP)

Example config.json
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

Configuration Reference
targets

List of domains to measure.

Example:

"targets": ["docs.example.com", "console.example.com"]

port

Port used for traceroute, ping, and HTTP measurements.

"port": 443

traceroute_enabled

Enable/disable traceroute phase.

true | false

ping_enabled

Enable/disable ping phase.

true | false

http_enabled

Enable/disable HTTP phase.

true | false

traceroute_protocol

Protocol used for traceroute:

TCP

UDP

ICMP (depending on API support)

ping_protocol

Protocol used for ping:

ICMP

TCP

http_protocol

HTTP protocol:

HTTP

HTTPS

method

HTTP method:

GET

POST

HEAD

countries

Defines probe distribution per country.

Format:

[
  {"DE": 10},
  {"IT": 8},
  {"ES": 5}
]


Meaning:

10 probes from Germany

8 probes from Italy

5 probes from Spain

check_hops

Optional mapping of hop aliases to IP addresses.

Used during traceroute analysis to match specific network hops.

Example:

"check_hops": {
  "internet_line1": "1.2.3.4",
  "internet_line2": "5.6.7.8"
}


If traceroute encounters these IPs, results will be grouped per hop alias.

Installation
pip install requests prometheus-client

Usage
Basic Run
python3 globaping.py --config config.json

With API Token
python3 globaping.py --config config.json --token YOUR_API_TOKEN

Export to JSON
python3 globaping.py --config config.json --json-output results.json

Export to CSV
python3 globaping.py --config config.json --csv-output results.csv


CSV format:

target,country,hop,ping_avg,http_avg

Prometheus Textfile Export

Useful for node_exporter textfile collector:

python3 globaping.py \
  --config config.json \
  --prometheus-output /var/lib/node_exporter/globalping.prom

Prometheus HTTP Exporter Mode

Starts HTTP server exposing metrics endpoint.

python3 globaping.py \
  --config config.json \
  --prometheus-http \
  --listen 0.0.0.0:9105 \
  --interval 300


Metrics available at:

http://0.0.0.0:9105/metrics

Exported Metrics
globalping_ping_avg_ms{target="",country=""}
globalping_http_total_avg_ms{target="",country=""}

StatsD Export
python3 globaping.py \
  --config config.json \
  --statsd-output 127.0.0.1:8125


Metrics format:

globalping.<target>.<country>.ping_avg
globalping.<target>.<country>.http_avg

Example Flow (With Current Config)

Given your config:

Targets:

docs.example.com

console.example.com

Countries:

DE (10 probes)

IT (8 probes)

ES (5 probes)

Enabled:

✅ Traceroute

❌ Ping

✅ HTTP

Flow:

Run TCP traceroute from DE, IT, ES.

Extract ASN from traceroute probes.

Build ASN-based follow-up locations.

Run HTTPS GET HTTP measurements from those ASN locations.

Aggregate:

Per country average HTTP time

Per country + matched hop alias

Print summary and export if requested.

Rate Limits

At the end of execution, the script prints API rate limits retrieved from Globalping:

Limit: X
Remaining: Y
Reset in: HH:MM:SS

Architecture Summary
Config → Traceroute → ASN Extraction
        ↓
     HTTP/Ping
        ↓
Aggregation
        ↓
Export (JSON / CSV / Prom / StatsD)

Use Cases

🌍 Multi-country latency monitoring

🛰 ISP/ASN path validation

🔎 Detect routing differences between providers

📊 Prometheus-based SLO monitoring

📈 External uptime and performance checks

Notes

If traceroute_enabled is true, follow-up measurements are ASN-based.

If disabled, measurements use country-based limits only.

Duplicated ASN probes are preserved intentionally to keep probe distribution accurate.

License

Internal / Custom use.
Adjust as needed for your environment.
