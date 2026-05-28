#!/usr/bin/env python3
"""
Reads config/provision.yml and generates:
  - homepage/config/settings.yaml
  - homepage/config/widgets.yaml
  - homepage/config/services.yaml
  - terraform/terraform.tfvars

Uses only Python stdlib — no third-party packages required.
"""

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request


def parse_provision_yaml(path):
    """Parse a flat key: value YAML file without a YAML library."""
    config = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if ":" in line:
                key, _, value = line.partition(":")
                value = value.strip().strip('"').strip("'")
                config[key.strip()] = value
    return config


def geocode_city(city, api_key):
    """
    Resolve city name to lat/lon using the OpenWeatherMap Geocoding API.
    This API is included in the free OWM tier.
    """
    url = (
        "https://api.openweathermap.org/geo/1.0/direct"
        f"?q={urllib.parse.quote(city)}&limit=1&appid={api_key}"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(
            f"ERROR: Geocoding API returned HTTP {exc.code}. "
            "Check your openweathermap_api_key in config/provision.yml.",
            file=sys.stderr,
        )
        sys.exit(1)
    except urllib.error.URLError as exc:
        print(f"ERROR: Could not reach geocoding API: {exc.reason}", file=sys.stderr)
        sys.exit(1)

    if not data:
        print(
            f"ERROR: City '{city}' not found. "
            "Check the city value in config/provision.yml.",
            file=sys.stderr,
        )
        sys.exit(1)

    return data[0]["lat"], data[0]["lon"]


def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content)
    print(f"  wrote {os.path.relpath(path)}")


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.dirname(script_dir)

    provision_path = os.path.join(project_root, "config", "provision.yml")
    if not os.path.exists(provision_path):
        print(f"ERROR: {provision_path} not found", file=sys.stderr)
        sys.exit(1)

    config = parse_provision_yaml(provision_path)

    required_keys = [
        "region", "instance_type", "server_name",
        "openweathermap_api_key", "city", "ssh_key_name",
    ]
    for key in required_keys:
        if key not in config:
            print(
                f"ERROR: Missing required key '{key}' in config/provision.yml",
                file=sys.stderr,
            )
            sys.exit(1)

    if config["openweathermap_api_key"] == "REPLACE_WITH_YOUR_KEY":
        print(
            "ERROR: Replace the placeholder openweathermap_api_key in config/provision.yml",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Geocoding '{config['city']}' via OpenWeatherMap...")
    lat, lon = geocode_city(config["city"], config["openweathermap_api_key"])
    print(f"  lat={lat:.4f}, lon={lon:.4f}")

    print("Generating configs...")

    write_file(
        os.path.join(project_root, "homepage", "config", "settings.yaml"),
        f'title: "{config["server_name"]}"\n'
        "theme: dark\n"
        "color: slate\n",
    )

    write_file(
        os.path.join(project_root, "homepage", "config", "widgets.yaml"),
        f'- weather:\n'
        f'    label: "{config["city"]}"\n'
        f'    latitude: {lat:.4f}\n'
        f'    longitude: {lon:.4f}\n'
        f'    units: metric\n'
        f'    provider: openweathermap\n'
        f'    apiKey: "{config["openweathermap_api_key"]}"\n'
        f'    cache: 5\n'
        f'- datetime:\n'
        f'    text_size: xl\n'
        f'    format:\n'
        f'      timeStyle: short\n'
        f'      dateStyle: long\n'
        f'      hour12: true\n'
        f'- search:\n'
        f'    provider: google\n'
        f'    target: _blank\n',
    )

    write_file(
        os.path.join(project_root, "homepage", "config", "services.yaml"),
        "# Add service cards here. See https://gethomepage.dev/configs/services/\n"
        "- My Server: []\n",
    )

    write_file(
        os.path.join(project_root, "terraform", "terraform.tfvars"),
        f'region        = "{config["region"]}"\n'
        f'instance_type = "{config["instance_type"]}"\n'
        f'server_name   = "{config["server_name"]}"\n'
        f'ssh_key_name  = "{config["ssh_key_name"]}"\n',
    )

    print("Done.")


if __name__ == "__main__":
    main()
