FROM python:3.12

COPY requirements.txt /requirements.txt

RUN python -m pip install -r /requirements.txt

RUN mkdir /app
COPY *.py /app
WORKDIR /app

ENV ORGANISATION=
ENV API_KEY=
ENV API_SECRET=
ENV MQTT_SERVER=
ENV MQTT_PORT=1883

CMD python -u nicehash2mqtt.py --organisation ${ORGANISATION} --api_key ${API_KEY} --api_secret ${API_SECRET} --mqtt_server ${MQTT_SERVER} --mqtt_port ${MQTT_PORT}
