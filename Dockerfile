# ---------- Builder stage ----------
FROM debian:trixie-slim AS builder

ARG GSTREAMER_VERSION=1.28.8
# Vulkan Video needs headers >= 1.4.317, trixie ships 1.4.309 (headers only, the loader stays Debian's)
ARG VULKAN_HEADERS_VERSION=1.4.360

ENV DEBIAN_FRONTEND=noninteractive

# Core build deps
RUN apt-get update && apt-get install -yq --no-install-recommends \
  build-essential meson ninja-build pkg-config git ca-certificates nasm \
  python3 python3-dev python-gi-dev gobject-introspection libgirepository1.0-dev \
  libglib2.0-dev libxml2-dev libffi-dev \
  libjpeg-dev libpng-dev libvorbis-dev libogg-dev libopus-dev \
  libasound2-dev libpulse-dev libcairo2-dev libpango1.0-dev libfreetype-dev flex bison \
  && rm -rf /var/lib/apt/lists/*

# Targeted plugin deps
RUN apt-get update && apt-get install -yq --no-install-recommends \
  libx264-dev libx265-dev libopenh264-dev libaom-dev libtheora-dev \
  libwebp-dev librsvg2-dev \
  libsrt-openssl-dev librtmp-dev libshout-dev libvo-aacenc-dev \
  libvulkan-dev libshaderc-dev glslc \
  libva-dev libdrm-dev libvpx-dev libgudev-1.0-dev \
  ladspa-sdk frei0r-plugins-dev \
  libsoup-3.0-dev libcurl4-openssl-dev \
  zlib1g-dev libssl-dev bash-completion \
  && rm -rf /var/lib/apt/lists/*

# WPE/WebKit + FDO backend for wpesrc
RUN apt-get update && apt-get install -yq --no-install-recommends \
  libwpewebkit-2.0-dev libwpe-1.0-dev libwpebackend-fdo-1.0-dev \
  libwayland-dev wayland-protocols libxkbcommon-dev \
  libepoxy-dev libegl-dev libgles-dev libgl-dev libgbm-dev \
  && rm -rf /var/lib/apt/lists/*

WORKDIR /opt

# /usr/local/include is searched before /usr/include, so these shadow libvulkan-dev's headers
RUN git clone --depth 1 -b v${VULKAN_HEADERS_VERSION} https://github.com/KhronosGroup/Vulkan-Headers.git && \
  cp -r Vulkan-Headers/include/vulkan Vulkan-Headers/include/vk_video /usr/local/include/

RUN git clone --depth 1 -b ${GSTREAMER_VERSION} https://gitlab.freedesktop.org/gstreamer/gstreamer.git

# Installs to /usr/local: WPE pulls in Debian's GStreamer 1.26 libraries under /usr/lib,
# /usr/local/lib is searched first so the two never overwrite each other.
RUN cd gstreamer && \
  meson setup builddir --prefix=/usr/local --libdir=lib --buildtype=release \
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
  ninja -C builddir install && \
  ldconfig

# ---------- Rust plugin builder ----------
# Inherits /usr/local with GStreamer 1.28 from builder, just adds rust toolchain
FROM builder AS rust-builder

RUN apt-get update && apt-get install -yq --no-install-recommends curl clang \
  && rm -rf /var/lib/apt/lists/*
# Use rustup for newer rust (trixie ships 1.85, gst-plugins-rs needs 1.92+)
RUN curl https://sh.rustup.rs -sSf | sh -s -- -y --default-toolchain stable --profile minimal
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cargo install --locked cargo-c

ARG GST_RS_VERSION=gstreamer-1.28.8
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
FROM debian:trixie-slim AS runtime

ENV DEBIAN_FRONTEND=noninteractive

# non-free for intel-media-va-driver-non-free
RUN sed -i 's/^Components: main$/Components: main contrib non-free non-free-firmware/' /etc/apt/sources.list.d/debian.sources

# Runtime libs only
RUN apt-get update && apt-get install -yq --no-install-recommends \
  python3 python3-pip python3-gi python3-gi-cairo libpython3.13 \
  libglib2.0-0t64 libgirepository-1.0-1 libxml2 \
  libjpeg62-turbo libpng16-16t64 libvorbis0a libvorbisenc2 libogg0 libopus0 libmpg123-0t64 \
  libasound2t64 libpulse0 libcairo2 libcairo-gobject2 libpango-1.0-0 libpangocairo-1.0-0 libfreetype6 \
  libx264-164 libx265-215 libopenh264-8 libvpx9 libaom3 libtheora0 \
  libwebp7 libwebpmux3 librsvg2-2 \
  libsrt1.5-openssl librtmp1 libshout3 libvo-aacenc0 libsoup-3.0-0 libcurl4t64 \
  libvulkan1 libva2 libva-drm2 libdrm2 libgudev-1.0-0 \
  zlib1g libssl3t64 \
  graphviz curl ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# WPE/WebKit for wpesrc (pulls in Debian's GStreamer 1.26 libraries, shadowed by /usr/local/lib)
RUN apt-get update && apt-get install -yq --no-install-recommends \
  libwpewebkit-2.0-1 libwpe-1.0-1 libwpebackend-fdo-1.0-1 \
  bubblewrap xdg-dbus-proxy \
  libwayland-client0 libwayland-server0 libwayland-egl1 libwayland-cursor0 libxkbcommon0 libepoxy0 \
  fontconfig fonts-noto-core \
  && rm -rf /var/lib/apt/lists/*

# GPU: Mesa GL/EGL + VA-API + Vulkan drivers (AMD RADV, Intel ANV, software lavapipe).
# Mesa from trixie-backports: Vulkan Video encode needs Mesa 26.x, trixie ships 25.0
RUN echo 'deb http://deb.debian.org/debian trixie-backports main' > /etc/apt/sources.list.d/backports.list \
  && apt-get update && apt-get install -yq --no-install-recommends \
  libegl1 libgl1 libgles2 intel-media-va-driver-non-free \
  && apt-get install -yq --no-install-recommends -t trixie-backports \
  libgbm1 libgl1-mesa-dri libegl-mesa0 libglx-mesa0 mesa-va-drivers mesa-vulkan-drivers \
  && rm -rf /var/lib/apt/lists/*

# LADSPA runtime + broadcast audio plugin collections:
#   zam-plugins: Zam compressors, gate, multiband, tube
#   lsp-plugins-ladspa: LSP pro audio suite — parametric EQ, de-esser,
#     multiband comp, sidechain comp, ISP limiter, gate, stereo imager
# frei0r video effects (100+ filters: pixelate, cartoon, distort, glow, etc.)
RUN apt-get update && apt-get install -yq --no-install-recommends \
  ladspa-sdk zam-plugins lsp-plugins-ladspa frei0r-plugins \
  && rm -rf /var/lib/apt/lists/*

COPY --from=builder /usr/local /usr/local
# Rust gst-plugins-rs (audiofx + optional livesync/fallbackswitch)
COPY --from=rust-builder /install/gst-plugins-rs/gstreamer-1.0/*.so /usr/local/lib/gstreamer-1.0/
RUN ldconfig

# GStreamer typelibs and gst-python overrides live under /usr/local
ENV GI_TYPELIB_PATH=/usr/local/lib/girepository-1.0
ENV PYTHONPATH=/usr/local/lib/python3/dist-packages

COPY . /app
WORKDIR /app
RUN cp config-example.toml config.toml

RUN pip install . --ignore-installed --break-system-packages

# Non-root user with video group (GPU access via /dev/dri)
RUN useradd -r -m -G video dove \
    && mkdir -p /var/dove/hls /crashes \
    && chown -R dove:dove /app /var/dove /crashes

EXPOSE 5000

# Suppress harmless warnings from WPE/WebKit/Mesa in headless container
ENV EGL_LOG_LEVEL=fatal
ENV NO_AT_BRIDGE=1
ENV DBUS_SESSION_BUS_ADDRESS=disabled:
ENV WEBKIT_DISABLE_SANDBOX_THIS_IS_DANGEROUS=1

USER dove

# Pre-scan GStreamer plugins at build time (baked registry = instant startup, no warnings on first run)
RUN gst-inspect-1.0 > /dev/null 2>&1

CMD ["python3", "-m", "dove.main", "--config", "/app/config.toml"]
