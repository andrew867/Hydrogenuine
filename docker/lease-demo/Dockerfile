# Capability-lease demo container — SIMULATED demos only, no hardware,
# no network egress at runtime, non-root, local volume for operator state.
FROM python:3.13-slim AS runtime

LABEL org.opencontainers.image.title="hg-lease-demo" \
      org.opencontainers.image.description="Conversational capability leasing — SIMULATED demos and setup wizard"

RUN useradd --create-home --uid 10001 lease
WORKDIR /app

COPY docker/lease-demo/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# OSS-core packages and the minimal kernel slice they compose with.
COPY hg_core /app/hg_core
COPY hg_gpp /app/hg_gpp
COPY hg_srp /app/hg_srp
COPY hg_gateway /app/hg_gateway
COPY hg_runtime /app/hg_runtime
COPY hg_csm /app/hg_csm
COPY hg_hal /app/hg_hal
COPY hg_mel /app/hg_mel
COPY hg_oea /app/hg_oea
COPY hg_ter /app/hg_ter
COPY hg_ueak /app/hg_ueak
COPY hg_lease /app/hg_lease
COPY config /app/config
COPY tests/lease /app/tests/lease
COPY pyproject.toml /app/pyproject.toml
COPY docker/lease-demo/entrypoint.py /app/entrypoint.py

ENV PYTHONPATH=/app \
    PYTHONDONTWRITEBYTECODE=1 \
    HG_LEASE_HOME=/data

RUN mkdir /data && chown lease:lease /data /app
VOLUME ["/data"]
USER lease

HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -m hg_lease.setup_wizard --home /data --diagnostics || exit 1

ENTRYPOINT ["python", "/app/entrypoint.py"]
CMD ["all"]
