FROM python:3.9-slim
ENV PYTHONUNBUFFERED=1
WORKDIR /embedding
COPY . /embedding
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt