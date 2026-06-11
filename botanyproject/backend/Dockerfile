FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Install Python deps first for better layer caching.
# REQUIREMENTS=dev for local, prod for the server image.
ARG REQUIREMENTS=dev
COPY requirements/ requirements/
# wheels/ is an optional local wheelhouse for environments where the build host
# cannot reach PyPI (e.g. broken container DNS). Populate it with
# `make wheels` / the documented pip download step; empty in CI/prod where the
# normal index install (the `||` fallback) is used.
COPY wheels/ /wheels/
RUN pip install --no-index --find-links=/wheels -r requirements/${REQUIREMENTS}.txt \
    || pip install -r requirements/${REQUIREMENTS}.txt

COPY . .
RUN chmod +x /app/entrypoint.sh

EXPOSE 8000

# entrypoint.sh uses `exec`, so the app process becomes PID 1 and receives signals.
ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["dev"]
