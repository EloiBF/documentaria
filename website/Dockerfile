FROM python:3.9-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /website
COPY . /website
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt