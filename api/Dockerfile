FROM python:3.11-slim-bookworm

ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
ENV PYTHONPATH=/app

RUN apt-get update && \
    apt-get install -yq \
    gstreamer1.0-wpe \
    gstreamer1.0-tools \
    gstreamer1.0-rtsp \
    gstreamer1.0-plugins-ugly  \
    gstreamer1.0-plugins-good  \
    gstreamer1.0-plugins-base-apps  \
    gstreamer1.0-plugins-bad-apps  \
    gstreamer1.0-plugins-bad  \
    gstreamer1.0-libav \
    gstreamer1.0-nice \
    libcairo2 \
    libcairo2-dev \
    libgirepository-1.0-1 \
    libgirepository1.0-dev  \
    gstreamer1.0-plugins-bad \
    gir1.2-gst-plugins-bad-1.0 \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0  \
    graphviz \
    curl



# currently we install gst-interpipe manually
RUN curl -JO https://people.debian.org/~birger/aequee2XOhwa7oow/gst-interpipe_1.1.8-1_amd64.deb && dpkg -i gst-interpipe_1.1.8-1_amd64.deb

RUN  pip install --upgrade pip 


COPY . /app
WORKDIR /app

RUN     pip install . --ignore-installed

EXPOSE 5000

CMD ["python3", "/app/main.py"]
