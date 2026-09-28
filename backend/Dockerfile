FROM python:3.12-slim

WORKDIR /code

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# INSTALL_DEV=true instala também pytest, ruff, etc. (o docker-compose ativa-o).
# Uma imagem de produção constrói-se com o valor por omissão (false).
ARG INSTALL_DEV=false

COPY requirements.txt requirements-dev.txt ./
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$INSTALL_DEV" = "true" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

RUN adduser --disabled-password --no-create-home appuser
USER appuser

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
