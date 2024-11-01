FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10


RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev 

COPY ./requirements.txt /app/requirements.txt

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

COPY . /app
WORKDIR /app
ENV APP_MODULE=teledash.app:app
