# hcloud-usage-exporter

Exports HCloud usage as prometheus metrics.

```
docker run --rm \
    -p 3000:3000 \
    -v /dev/shm:/dev/shm \
    -e HCLOUD_USERNAME=... \
    -e HCLOUD_PASSWORD=... \
    -e HCLOUD_TOTP_SECRET=... \
    ghcr.io/NiklasRosenstein/hcloud-usage-exporter
```
