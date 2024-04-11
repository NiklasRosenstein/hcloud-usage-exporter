
.PHONY: default
default:
	@echo "Please specify a target"

.PHONY: build
build:
	BUILDKIT_PROGRESS=plain docker build . -t hcloud-usage-exporter

.PHONY: run
run: build
	docker run --name hue --rm -it -p 3000:3000 \
		-v /dev/shm:/dev/shm \
		-e HCLOUD_USERNAME=${HCLOUD_USERNAME} \
		-e HCLOUD_PASSWORD=${HCLOUD_PASSWORD} \
		-e HCLOUD_TOTP_SECRET=${HCLOUD_TOTP_SECRET} \
		hcloud-usage-exporter

.PHONY: logtrail
logtrail:
	docker exec -it hue bash -c 'tail -f /var/log/supervisor/hcloud*'
