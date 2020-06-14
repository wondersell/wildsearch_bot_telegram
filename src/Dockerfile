FROM python:3.8-slim

COPY requirements.txt ./

RUN apt-get update && \
  apt-get --no-install-recommends --assume-yes install build-essential libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

RUN pip install --no-cache-dir -r requirements.txt

RUN pip install uwsgi

RUN mkdir -p /srv

WORKDIR /