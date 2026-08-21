FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV HG_ENV=Demo
ENV HG_GATEWAY_API_KEY=demo-api-key
ENV HG_GATEWAY_STORE=sqlite
ENV HG_GATEWAY_DB_PATH=/data/gateway.sqlite3

WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY community_ui ./community_ui
COPY examples ./examples
COPY tests ./tests
COPY docs/community ./docs/community
COPY hg_lib ./hg_lib
COPY hg_cli ./hg_cli
COPY hg_core ./hg_core
COPY hg_gateway ./hg_gateway
COPY hg_gpp ./hg_gpp
COPY hg_hal ./hg_hal
COPY hg_knowledge ./hg_knowledge
COPY hg_lease ./hg_lease
COPY hg_llm ./hg_llm
COPY hg_memory ./hg_memory
COPY hg_oea ./hg_oea
COPY hg_operator_auth ./hg_operator_auth
COPY hg_realtime ./hg_realtime
COPY hg_runtime ./hg_runtime
COPY hg_soar ./hg_soar
COPY hg_ueak ./hg_ueak
COPY hg_workbench ./hg_workbench

RUN pip install --no-cache-dir -e .

EXPOSE 8000

CMD ["uvicorn", "hg_gateway.main:app", "--host", "0.0.0.0", "--port", "8000"]
