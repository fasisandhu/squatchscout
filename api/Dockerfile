FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
WORKDIR /app
# Dependencies first, from pyproject.toml alone (no `app` package present yet — setuptools
# builds an empty wheel that still declares every [project.dependencies] pin, so pip installs
# them all). This layer only re-runs when pyproject.toml itself changes, not on every source
# edit, which matters on the spec's 1 GB t3.micro target where a full dependency reinstall is
# both slow (~140s) and OOM-prone.
COPY pyproject.toml ./
COPY alembic.ini ./
RUN pip install --upgrade pip && pip install .
# Now the real source, and a second install that only (re)builds our own package — --no-deps
# skips dependency resolution entirely, so this layer is fast and doesn't touch the layer above.
COPY app ./app
COPY alembic ./alembic
RUN pip install --no-deps .
RUN useradd -m appuser && chown -R appuser /app
USER appuser
# Declared last so a new commit SHA alone doesn't bust the dependency/source layers above.
ARG APP_VERSION=dev
ENV APP_VERSION=$APP_VERSION
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"]
