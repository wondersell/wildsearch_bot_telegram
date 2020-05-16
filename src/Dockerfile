FROM python:3.8-slim

COPY requirements.txt ./

RUN apt-get update && apt-get --assume-yes install git

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && \
  apt-get --no-install-recommends --assume-yes install build-essential

RUN pip install uwsgi

RUN mkdir -p /srv

WORKDIR /