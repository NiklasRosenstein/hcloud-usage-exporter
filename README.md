<p align="center"><img src="./hcloud-usage-exporter.jpg"></p>

<h1 align="center">hcloud-usage-exporter</h1>

<p align="center">Export HCloud cost totals as Prometheus metrics. Uses Selenium to scrape data from the Hetzner Cloud
web interface.</p>

## Usage

* The container image is available from `ghcr.io/niklasrosenstein/hcloud-usage-exporter`.
* The exporter listens on port `3000` and serves metrics at `/`.
* The exporter requires the following environment variables:
  * `HCLOUD_USERNAME`: The Hetzner Cloud username.
  * `HCLOUD_PASSWORD`: The Hetzner Cloud password.
  * `HCLOUD_TOTP_SECRET`: The Hetzner Cloud TOTP secret, if two-factor authentication is enabled.
* The default scrape interval is 5 minutes.

__Example__

```bash
$ docker run --rm -d \
    -p 3000:3000 \
    -v /dev/shm:/dev/shm \
    -e HCLOUD_USERNAME=... \
    -e HCLOUD_PASSWORD=... \
    -e HCLOUD_TOTP_SECRET=... \
    ghcr.io/niklasrosenstein/hcloud-usage-exporter
$ curl localhost:3000
...
```

## Metrics

* `hcloud_usage_exporter_project_cost_eur{project_name}`
* `hcloud_usage_exporter_state{hcloud_usage_exporter_state="pending|healthy|error}`
* ... todo

## Troubleshooting

### Chrome crashes

Considering granting the pod a larger `/dev/shm` volume, or mount the host's `/dev/shm` into the container.

### Service logs

You can find them under `/var/log/supervisor/hcloud-usage-exporter*.log`.

### Inspect page state on error

A history of the five last page loads are stored in `/var/lib/hcloud-usage-exporter/error-history`, allowing you
to inspect the screenshot and page source when an error occurs.
