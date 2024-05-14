FROM debian:testing-slim as builder

ARG INTERPIPE_VERSION=develop
ENV LC_ALL=C.UTF-8
ENV LANG=C.UTF-8
RUN apt update && \
    apt install -yq git build-essential meson ninja-build  libgstreamer1.0-dev  libgstreamer-plugins-base1.0-dev gtk-doc-tools wget libva-dev gstreamer1.0-vaapi && \
    git clone -b ${INTERPIPE_VERSION} https://github.com/RidgeRun/gst-interpipe.git /install/interpipe && \
    cd /install/interpipe && \
    wget https://github.com/RidgeRun/gst-interpipe/pull/102.diff && \
    patch -p1 < 102.diff && \
    mkdir -p build && \
    mkdir -p /gst-interpipe && \
    meson setup build --prefix=/gst-interpipe && \
    ninja -C build && \
    ninja -C build install && \
    rm -rf /install



FROM debian:testing-slim as runtime

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
    gstreamer1.0-vaapi \
    gstreamer1.0-nice \
    python3-gst-1.0 \
    libgirepository1.0-dev  \
    libcairo2 \
    libgirepository-1.0-1 \
    gstreamer1.0-plugins-bad \
    gir1.2-gst-plugins-bad-1.0 \
    gir1.2-gstreamer-1.0 \
    gir1.2-gst-plugins-base-1.0  \
    graphviz \
    curl \
    libcairo2-dev \
    python3-pip \
    python3-poetry

COPY --from=builder /gst-interpipe/ /usr/

COPY . /app
WORKDIR /app

#@TODO run as user && pipenv
RUN     pip install . --ignore-installed --break-system-packages

RUN apt remove -y libcairo2-dev  libgirepository1.0-dev && apt autoremove -y && apt clean

EXPOSE 5000

CMD ["python3", "/app/main.py", "--config", "/app/config.toml"]
