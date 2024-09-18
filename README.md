## DOVE - Online Video Editor

DOVE is an API driven Video/Audio Editor for live mixing with an intuitive web based Interface.

It uses the [gstreamer](https://gstreamer.freedesktop.org) multimedia framework as backend and [gst-interpipe](https://github.com/ridgerun/gst-interpipe) for connecting pipelines.

Development for the [Nuxt3](https://nuxt.com/) based frontend happens [here](https://github.com/dorftv/dove-frontend)

DOVE is heavily inspired by [bbc/brave](https://github.com/bbc/brave)


### Features
Basic usage can be described as following
>  **Inputs** can be mixed in **Scenes**.
   **Scenes** can be cut to **Program**.
   **Program** can have **Outputs**.

Inputs, Scenes and Program can have a preview.
Currently HLS is available for preview with a latency of 1-5 seconds. Future versions will include a WEBRTC preview with subsecond latency.

#### Inputs
* playbin3
* playlists ( mix html and video)
* wpesrc ( view html. option to not draw background for overlays )
* NodeCG ( embed graphics via wpesrc / embed dashboards with iframes )
* yt-dlp (Play all supported Urls with playbin3)
* audio/videotestsrc
* webrtc (planned)
* ... more to come

#### Scenes
with scenes inputs can be mixed.
Scenes are a combination of the gstreamer elements [compositor](https://gstreamer.freedesktop.org/documentation/compositor/index.html) and [liveadder](https://gstreamer.freedesktop.org/documentation/audiomixer/liveadder.html).
They are used for mixing inputs. A scene can have multiple sink pads ( input slots )
Each sink pad supports alpha,width,height,xpos,ypos,zorder properties for video, and volume property for audio.

#### Outputs
* srt ( srtsink, srtserversink )
* decklink
* hls ( for preview)
* webrtc ( for preview, planned )
* shoutcast
* rtmp
* webrtc ( planned )
* ... more to come


### Dependencies
Development happens on Debian, so currently the following versions are recommended.

* python >= version 3.11
* gst-interpipe ( develop branch )
* gstreamer1.0 > 1.22)

there is no package for gst-interpipe in debian bookworm. follow the [compilation guide](https://developer.ridgerun.com/wiki/index.php/GstInterpipe_-_Building_and_Installation_Guide) or look at (or use) the [Dockerfile](/Dockerfile)


### Getting Started

#### pipenv
@TODO

#### Docker
The easiest way for getting started is using the provided docker image or build the image yourself using the Dockerfile.
The default Dockerfile uses Debian testing which includes gstreamer 1.24. There is a Dockerfile.bookworm that also works with gstreamer 1.22.

##### Docker

caps and security opts are needed for wpesrc.

```
curl  https://raw.githubusercontent.com/dorftv/dove/main/config-example.toml -o /tmp/config.toml && \
  -e LIBGL_ALWAYS_SOFTWARE=true  -v
docker run -p 5000:5000 \
 -e LIBGL_ALWAYS_SOFTWARE=true \
 --cap-add SYS_ADMIN --cap-add CAP_NET_ADMIN \
 --security-opt apparmor=unconfined --security-opt seccomp=unconfined \
 -v /tmp/config.toml:/app/config.toml -it \
  ghcr.io/dorftv/dove:latest

```

you can add the following to utilize your gpu via vaapi

```
-v /tmp/.X11-unix:/tmp/.X11-unix -e DISPLAY=$DISPLAY --device=/dev/dri

```


##### Docker-compose
gstreamer and so DOVE, can use your GPU for decoding. [docker-compose.vaapi.yml](/docker-compose.vaapi.yml) provides an example for using vaapi.


```
git clone https://github.com/dorftv/dove.git  && cd dove

# Currently a empty config files are not supported.
# to start you can copy the example config.
cp -f config-example.toml config.toml

docker compose up -d
```

point your Browser to [http://localhost:5000](http://localhost:5000)

### Notes

more documentation will follow.




