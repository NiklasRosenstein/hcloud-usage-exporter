FROM selenium/standalone-chrome
RUN pip install -U pip && pip install pipx && pipx install pdm
WORKDIR /app
COPY . /app
RUN pdm install
ENTRYPOINT [ "pdm", "run", "python", "main.py" ]
