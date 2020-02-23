FROM python:3.8-slim

RUN curl -L https://raw.githubusercontent.com/DataDog/datadog-agent/master/cmd/agent/install_script.sh

COPY requirements.txt ./

RUN pip install --no-cache-dir -r requirements.txt

RUN apt-get update && \
  apt-get --no-install-recommends --assume-yes install build-essential

RUN pip install uwsgi

RUN mkdir -p /srv

WORKDIR /