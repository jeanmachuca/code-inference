# syntax=docker/dockerfile:1
FROM python:3.12-alpine3.21

WORKDIR /app

RUN apk add --no-cache ca-certificates

COPY src/services/api/requirements.txt src/services/api/pytest.ini ./
RUN pip install --no-cache-dir -r requirements.txt

COPY src/services/api/app ./app
COPY tests ./tests

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
