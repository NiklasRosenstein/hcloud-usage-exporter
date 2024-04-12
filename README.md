<p align="center"><img src="./hcloud-usage-exporter.jpg"></p>

<h1 align="center">hcloud-usage-exporter</h1>

<p align="center">Export HCloud cost totals as prometheus metrics.</br>
Uses Selenium to scrape the data from the Hetzner Cloud web interface.</p>

## Usage

```
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

## Exported metrics

### Gauge `hcloud_usage_total_eur{project_name="...",}`

The total cost of the project in EUR.

### Counter `hcloud_usage_logins`
### Counter `hcloud_usage_fetches`
### Counter `hcloud_usage_errors`

## Troubleshooting

### Chrome crashes

Considering granting the pod a larger `/dev/shm` volume, or mount the host's `/dev/shm` into the container.

### Service logs

You can find them under `/var/log/supervisor/hcloud-usage-exporter*.log`.

### Inspect page state on error

A history of the five last page loads are stored in `/var/lib/hcloud-usage-exporter/error-history`, allowing you
to inspect the screenshot and page source when an error occurs.
