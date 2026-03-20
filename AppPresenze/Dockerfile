# syntax=docker/dockerfile:1

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dipendenze di sistema per conversione DOCX -> PDF via LibreOffice
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        libreoffice \
        fonts-liberation \
        libfontconfig1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt \
    && pip install gunicorn

COPY . .

EXPOSE 7999

# Avvio con gunicorn (Django WSGI)
CMD ["gunicorn", "-c", "gunicorn.conf.py", "AppPresenze.wsgi:application"]
