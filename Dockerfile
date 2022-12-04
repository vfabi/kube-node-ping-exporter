FROM python:3.6-alpine3.8
ADD app /app
RUN pip3 install --upgrade pip && pip3 install -r  /app/requirements.txt && apk add --no-cache fping
WORKDIR /app
# ENV PYTHONPATH "/app/"
ENTRYPOINT ["python3", "/app/main.py"]
