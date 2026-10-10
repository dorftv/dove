# Native Install

For Docker setup see the [README](../README.md). This page covers running DOVE directly from a Python venv on Linux.

## System packages

Pick your distro.

**Arch / CachyOS** (GStreamer 1.28 in official repos):

```bash
sudo pacman -S --needed \
  gstreamer gst-plugins-base gst-plugins-good gst-plugins-bad \
  gst-plugins-ugly gst-libav gst-python \
  gst-plugin-rsaudiofx gst-plugin-livesync gst-plugin-fallbackswitch \
  gst-plugin-wpe python python-gobject python-pip \
  wpewebkit wpebackend-fdo frei0r-plugins lsp-plugins ladspa
```

**Debian Trixie:**

Trixie ships GStreamer 1.26, which DOVE supports (`vulkanh264enc` needs 1.28 — use the default Docker image for that). `gstreamer1.0-fdkaac` is in the `non-free` component; enable it in `/etc/apt/sources.list.d/debian.sources` first.

```bash
sudo apt install --no-install-recommends \
  python3 python3-pip python3-venv python3-gi python3-gi-cairo \
  gobject-introspection libgirepository-1.0-1 libcairo2-dev \
  gstreamer1.0-tools gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly gstreamer1.0-libav \
  gstreamer1.0-nice gstreamer1.0-wpe gstreamer1.0-vaapi gstreamer1.0-fdkaac gstreamer1.0-x \
  gir1.2-gstreamer-1.0 gir1.2-gst-plugins-base-1.0 gir1.2-gst-plugins-bad-1.0 \
  libwpe-1.0-1 libwpebackend-fdo-1.0-1 libwpewebkit-2.0-1 \
  bubblewrap xdg-dbus-proxy dbus at-spi2-core \
  mesa-va-drivers mesa-vulkan-drivers fonts-noto-core graphviz \
  frei0r-plugins lsp-plugins-ladspa zam-plugins
```

`gst-plugins-rs` (audiofx for ebur128level/audioloudnorm, livesync, fallbackswitch) is not packaged on Trixie — build from source (matches `Dockerfile.trixie`):

```bash
sudo apt install -y build-essential clang pkg-config libssl-dev git curl \
  libgstreamer1.0-dev libgstreamer-plugins-base1.0-dev
# rustup: the plugins need Rust 1.92+, Trixie ships 1.85
curl https://sh.rustup.rs -sSf | sh -s -- -y --profile minimal
. "$HOME/.cargo/env"
cargo install cargo-c
git clone --depth 1 -b gstreamer-1.28.8 https://gitlab.freedesktop.org/gstreamer/gst-plugins-rs.git /tmp/gst-plugins-rs
cd /tmp/gst-plugins-rs
cargo cinstall --libdir=/tmp/gst-rs --package gst-plugin-audiofx
cargo cinstall --libdir=/tmp/gst-rs --package gst-plugin-livesync
cargo cinstall --libdir=/tmp/gst-rs --package gst-plugin-fallbackswitch
sudo cp /tmp/gst-rs/gstreamer-1.0/*.so /usr/lib/x86_64-linux-gnu/gstreamer-1.0/
```

## Backend (pip)

```bash
sudo install -d -o "$(id -un)" /var/dove   # HLS previews and recordings
python3 -m venv ~/dove-venv --system-site-packages
~/dove-venv/bin/pip install --pre dove-video-editor
MALLOC_MMAP_THRESHOLD_=131072 ~/dove-venv/bin/dove   # the variable bounds glibc memory growth
```

## Backend (venv)

**Python:** 3.12 or 3.13 required. **Do NOT use Python 3.14** — PyGObject + GStreamer interaction on 3.14 has known thread/asyncio bugs that cause GLib main-loop hangs on input deletion. The Docker images ship Python 3.13.

PyGObject lives in the system Python — the venv must inherit it:

```bash
cd dove
python -m venv .venv --system-site-packages
source .venv/bin/activate
pip install -e .

# config.toml is gitignored; create it with the standard 3-line header
printf '# DOVE config overrides\n# Values here override config-default.toml (per-section, not deep merge)\n# See config-default.toml for all available options\n' > config.toml

python -m dove.main --config config.toml
```

DOVE listens on `http://localhost:5000`.

## Backend (Poetry)

```bash
cd dove
poetry install
poetry run python -m dove.main --config config.toml
```

## Frontend

```bash
cd dove-frontend
npm install
npm run dev   # http://localhost:3000
```

The dev server proxies API/WebSocket/WHEP traffic to `http://localhost:5000` by default. Override with `DOVE_API=http://host:port` if the backend runs elsewhere.

## GStreamer debug

```bash
GST_DEBUG=2 GST_DEBUG_DUMP_DOT_DIR=/tmp python -m dove.main -c config.toml
```
