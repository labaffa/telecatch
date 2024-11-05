FROM python:3.10

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    libffi-dev \
    python3-dev 

COPY ./requirements.txt /app/requirements.txt
WORKDIR /app

RUN pip install --no-cache-dir --upgrade -r /app/requirements.txt

ADD . /app

CMD ["uvicorn", "teledash.app:app", "--host",  "0.0.0.0", "--port", "8000", "--workers", "1"]