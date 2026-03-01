# ---------- Builder stage ----------
FROM alpine:3.21 AS builder

ARG GSTREAMER_VERSION=1.28.2

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
  ladspa-dev \
  frei0r-plugins-dev \
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
    -Dgst-plugins-bad:ladspa=enabled \
    -Dgst-plugins-bad:frei0r=enabled \
    -Dtests=disabled && \
  ninja -C builddir && \
  ninja -C builddir install

# ---------- Rust plugin builder ----------
# Inherits /usr with GStreamer 1.28 from builder, just adds rust toolchain
FROM builder AS rust-builder

RUN apk add --no-cache clang gcc musl-dev curl pkgconfig openssl-dev zlib-dev
# Use rustup for newer rust (Alpine 3.21 ships 1.83, gst-plugins-rs 0.15 needs 1.92+)
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"
# Disable static crt so cargo-c links dynamically against system libs (avoids static lib chain)
ENV RUSTFLAGS="-C target-feature=-crt-static"
RUN cargo install --locked cargo-c

ARG GST_RS_VERSION=0.15
RUN git clone --depth 1 -b ${GST_RS_VERSION} \
    https://gitlab.freedesktop.org/gstreamer/gst-plugins-rs.git /opt/gst-plugins-rs

WORKDIR /opt/gst-plugins-rs
# Audio effects (ebur128level, audioloudnorm, audiornnoise, hrtfrender)
RUN cargo cinstall --libdir=/install/gst-plugins-rs --package gst-plugin-audiofx
# livesync for live source resync
RUN cargo cinstall --libdir=/install/gst-plugins-rs --package gst-plugin-livesync
# fallbackswitch/fallbacksrc for graceful failover
RUN cargo cinstall --libdir=/install/gst-plugins-rs --package gst-plugin-fallbackswitch

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
    bubblewrap xdg-dbus-proxy \
    wpewebkit libwpe libwpebackend-fdo wayland-libs-client libxkbcommon \
    fontconfig font-noto ca-certificates \
    mesa mesa-egl mesa-gl mesa-dri-gallium \
    mesa-vulkan-swrast mesa-vulkan-ati mesa-vulkan-intel

RUN apk add --no-cache openh264 x265 bash-completion curl libsoup

# LADSPA runtime + broadcast audio plugin collections:
#   zam-plugins-ladspa: Zam compressors, gate, multiband, tube
#   lsp-plugins-ladspa: LSP pro audio suite — parametric EQ, de-esser,
#     multiband comp, sidechain comp, ISP limiter, gate, stereo imager
RUN apk add --no-cache ladspa zam-plugins-ladspa lsp-plugins-ladspa

# frei0r video effects (100+ filters: pixelate, cartoon, distort, glow, etc.)
RUN apk add --no-cache frei0r-plugins

RUN apk add --no-cache     intel-media-driver      mesa-va-gallium
COPY --from=builder /usr /usr
# Rust gst-plugins-rs (audiofx + optional livesync/fallbackswitch)
COPY --from=rust-builder /install/gst-plugins-rs/ /usr/lib/gstreamer-1.0/

# Upgrade Mesa + deps from edge for Vulkan Video encode support (Mesa 26.x+)
RUN apk upgrade --no-cache \
    --repository=https://dl-cdn.alpinelinux.org/alpine/edge/main \
    mesa mesa-gbm mesa-dri-gallium mesa-egl mesa-gl mesa-va-gallium \
    mesa-vulkan-ati mesa-vulkan-intel mesa-vulkan-swrast \
    vulkan-loader libxcb wayland-libs-client libva

COPY . /app
WORKDIR /app
RUN cp config-example.toml config.toml

RUN pip install . --ignore-installed --break-system-packages

# Non-root user with video group (GPU access via /dev/dri)
RUN addgroup -S dove && adduser -S -G dove dove \
    && addgroup dove video \
    && mkdir -p /var/dove/hls /crashes \
    && chown -R dove:dove /app /var/dove /crashes

EXPOSE 5000

# Suppress harmless warnings from WPE/WebKit/Mesa in headless container
ENV EGL_LOG_LEVEL=fatal
ENV NO_AT_BRIDGE=1
ENV JSC_SIGNAL_FOR_GC=14
ENV DBUS_SESSION_BUS_ADDRESS=disabled:
ENV WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1

# Pre-scan GStreamer plugins at build time (baked registry = instant startup)
RUN gst-inspect-1.0 > /dev/null 2>&1

USER dove
CMD ["python3", "/app/main.py", "--config", "/app/config.toml"]
