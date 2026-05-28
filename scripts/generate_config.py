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
import re
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

    Tries the city string as-is first. If OWM returns no results and the
    city looks like "Name, ST" (US city with two-letter state), automatically
    retries as "Name,ST,US" which is the format OWM requires for US cities.
    """
    queries = [city]
    if re.search(r",\s*[A-Z]{2}$", city):
        queries.append(re.sub(r",\s*", ",", city) + ",US")

    for query in queries:
        url = (
            "https://api.openweathermap.org/geo/1.0/direct"
            f"?q={urllib.parse.quote(query)}&limit=1&appid={api_key}"
        )
        try:
            with urllib.request.urlopen(url, timeout=10) as resp:
                data = json.loads(resp.read().decode())
        except urllib.error.HTTPError as exc:
            print(
                f"ERROR: Geocoding API returned HTTP {exc.code}. "
                "Check the OWM_API_KEY secret — it may not be activated yet "
                "(new keys can take up to 2 hours).",
                file=sys.stderr,
            )
            sys.exit(1)
        except urllib.error.URLError as exc:
            print(f"ERROR: Could not reach geocoding API: {exc.reason}", file=sys.stderr)
            sys.exit(1)

        if data:
            return data[0]["lat"], data[0]["lon"]

    print(
        f"ERROR: City '{city}' not found by OpenWeatherMap.\n"
        "Try a more specific format, e.g. 'Mount Pleasant,SC,US' or just 'Charleston'.",
        file=sys.stderr,
    )
    sys.exit(1)


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

    required_keys = ["region", "instance_type", "server_name", "city", "ssh_key_name"]
    for key in required_keys:
        if key not in config:
            print(
                f"ERROR: Missing required key '{key}' in config/provision.yml",
                file=sys.stderr,
            )
            sys.exit(1)

    # API key is never stored in the repo — read it from the environment instead.
    # Locally: export OWM_API_KEY=your-key
    # In GitHub Actions: stored as the OWM_API_KEY repository secret
    api_key = os.environ.get("OWM_API_KEY", "").strip()
    if not api_key:
        print(
            "ERROR: OWM_API_KEY environment variable is not set.\n"
            "  Locally:         export OWM_API_KEY=your-key\n"
            "  GitHub Actions:  add OWM_API_KEY as a repository secret",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Geocoding '{config['city']}' via OpenWeatherMap...")
    lat, lon = geocode_city(config["city"], api_key)
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
        f'    apiKey: "{api_key}"\n'
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
