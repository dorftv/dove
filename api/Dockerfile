FROM python:3.11-slim-bookworm

ARG INTERPIPE_VERSION=develop
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

RUN apt install -yq git build-essential meson ninja-build  libgstreamer1.0-dev  libgstreamer-plugins-base1.0-dev gtk-doc-tools

RUN git clone -b ${INTERPIPE_VERSION} https://github.com/RidgeRun/gst-interpipe.git /install/interpipe && \
    cd /install/interpipe && \
    mkdir -p build && \
    meson setup build --prefix=/usr && \
    ninja -C build && \
    ninja -C build install && \
    rm -rf /install

#RUN apt-get purge  -y git build-essential meson ninja-build  libgstreamer1.0-dev  libgstreamer-plugins-base1.0-dev gtk-doc-tools #&& \
#    apt-get autoremove -y


RUN  pip install --upgrade pip 

COPY . /app
WORKDIR /app

RUN     pip install . --ignore-installed

EXPOSE 5000

CMD ["python3", "/app/main.py"]
