FROM selenium/standalone-chrome

USER root
RUN apt-get update && apt-get install -y python3-venv python3-pip && \
    pip install pipx && mkdir /opt/pipx && PIPX_HOME=/opt/pipx PIPX_BIN_DIR=/opt/pipx/bin pipx install pdm && \
    apt-get clean && rm -rf /var/lib/apt/lists/*
RUN ls -lA /home/seluser && chown -R seluser:seluser /home/seluser

USER seluser
ENV PATH="$PATH:/opt/pipx/bin"
RUN ls -lr /opt/pipx/bin
WORKDIR /app

COPY main.py pdm.lock pyproject.toml README.md /app/
RUN --mount=type=cache,target=/tmp/cache/pdm,uid=1200 \
    export PDM_CACHE_DIR=/tmp/cache/pdm && \
    pdm install -v --no-lock

COPY supervisord.conf /etc/supervisor/conf.d/hcloud-usage-exporter.conf

# ENTRYPOINT [ "pdm", "run", "python", "main.py" ]
