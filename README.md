# hcloud-usage-metrics

Exports HCloud usage as prometheus metrics.

```
docker run --rm \
    -p 3000:3000 \
    -e HCLOUD_USERNAME=... \
    -e HCLOUD_PASSWORD=... \
    -e HCLOUD_TOTP_SECRET=... \
    ghcr.io/NiklasRosenstein/hcloud-usage-metrics
```
