# ---------- Builder stage ----------
FROM alpine:3.21 AS builder

ARG GSTREAMER_VERSION=1.28.1

# Core build deps
RUN apk add --no-cache \
  build-base meson ninja pkgconfig git ca-certificates \
  python3 python3-dev py3-pip gobject-introspection-dev \
  glib-dev libxml2-dev libffi-dev \
  libjpeg-turbo-dev libpng-dev libvorbis-dev libogg-dev opus-dev \
  alsa-lib-dev pulseaudio-dev cairo-dev pango-dev freetype-dev flex bison 

# Targeted plugin deps
RUN apk add --no-cache \
  x264-dev \
  libsrt-dev \
  vulkan-loader-dev vulkan-headers \
  libva-dev libvpx-dev \
  zlib-dev openssl-dev make

WORKDIR /opt

# Upgrade Vulkan loader + headers from edge (need 1.4.x for Vulkan Video encoding)
RUN apk upgrade --no-cache \
    --repository=https://dl-cdn.alpinelinux.org/alpine/edge/main \
    vulkan-loader-dev vulkan-headers vulkan-loader

# Build librtmp (from rtmpdump) and install with a pkg-config file
RUN git clone https://git.ffmpeg.org/rtmpdump.git /opt/rtmpdump && \
    cd /opt/rtmpdump && \
    make SYS=posix && \
    make install prefix=/usr && \
    mkdir -p /usr/lib/pkgconfig && \
    printf "prefix=/usr\nexec_prefix=\${prefix}\nlibdir=\${exec_prefix}/lib\nincludedir=\${prefix}/include\n\nName: librtmp\nDescription: RTMP library\nVersion: 2.4\nLibs: -L\${libdir} -lrtmp\nCflags: -I\${includedir}/librtmp\n" > /usr/lib/pkgconfig/librtmp.pc

# WPE/WebKit + FDO backend for wpesrc
RUN apk add --no-cache \
  wpewebkit-dev libwpe-dev libwpebackend-fdo-dev \
  wayland-dev libxkbcommon-dev \
  libepoxy-dev mesa-dev


RUN git clone https://gitlab.freedesktop.org/gstreamer/gstreamer.git

RUN apk add --no-cache x265-dev openh264-dev bash-completion-dev libsoup-dev curl-dev
RUN apk add --no-cache shaderc-dev

# Configure targeted features with namespaced options
RUN cd gstreamer && \
  git checkout ${GSTREAMER_VERSION} && \
  meson setup builddir --prefix=/usr --buildtype=release \
    -Dgpl=enabled \
    -Dugly=enabled \
    -Dbad=enabled \
    -Dgood=enabled \
    -Dintrospection=enabled \
    -Dgst-plugins-bad:vulkan-video=enabled \
    -Dtests=disabled && \
  ninja -C builddir && \
  ninja -C builddir install

# ---------- Runtime stage ----------
FROM alpine:3.21 AS runtime

# Runtime libs only
RUN apk add --no-cache \
  python3 py3-pip py3-gobject3 \
  glib libjpeg-turbo libpng libvorbis opus \
  alsa-lib pulseaudio cairo pango freetype \
  x264 libsrt \
  vulkan-loader mesa \
  libva libvpx \
  zlib openssl


RUN apk add --no-cache \
    python3 py3-pip py3-poetry-core \
    gobject-introspection gobject-introspection-dev \
    cairo cairo-dev \
    graphviz curl

RUN apk add --no-cache \
    bubblewrap dbus xdg-dbus-proxy \
    wpewebkit libwpe libwpebackend-fdo wayland-libs-client libxkbcommon \
    fontconfig font-noto ca-certificates \
    mesa mesa-egl mesa-gl mesa-dri-gallium \
    mesa-vulkan-swrast mesa-vulkan-ati mesa-vulkan-intel

RUN apk add --no-cache openh264 x265 bash-completion curl libsoup

RUN apk add --no-cache     intel-media-driver      mesa-va-gallium
COPY --from=builder /usr /usr

# Upgrade Mesa + deps from edge for Vulkan Video encode support (Mesa 26.x+)
RUN apk upgrade --no-cache \
    --repository=https://dl-cdn.alpinelinux.org/alpine/edge/main \
    mesa mesa-gbm mesa-dri-gallium mesa-egl mesa-gl mesa-va-gallium \
    mesa-vulkan-ati mesa-vulkan-intel mesa-vulkan-swrast \
    vulkan-loader libxcb wayland-libs-client libva

COPY . /app
WORKDIR /app

RUN     pip install . --ignore-installed --break-system-packages

EXPOSE 5000

# Suppress harmless warnings from WPE/WebKit/Mesa in headless container
ENV EGL_LOG_LEVEL=fatal
ENV NO_AT_BRIDGE=1
ENV JSC_SIGNAL_FOR_GC=14

ENTRYPOINT ["/app/entrypoint.sh"]
