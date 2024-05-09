## DOVE - Online Video Editor

DOVE is an API driven Video/Audio Editor for managing live mixing with an intuitive web based Interface.

It uses the [gstreamer multimedia framework](https://gstreamer.freedesktop.org) as backend and [gst-interpipe](https://github.com/ridgerun/gst-interpipe) for connecting pipelines.

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
* playlists
* wpesrc
* yt-dlp (playbin3)
* audio/videotestsrc
* webrtc (planned)
* ....

#### Scenes
with scenes inputs can be mixed.
Scenes are a combination of the gstreamer elements [compositor](https://gstreamer.freedesktop.org/documentation/compositor/index.html) and [liveadder](https://gstreamer.freedesktop.org/documentation/audiomixer/liveadder.html).
They are used for mixing inputs. A scene can have multiple sink pads ( input slots )
Each sink pad supports alpha,width,height,xpos,ypos,zorder properties for video, and volume property for audio.

#### Outputs
* srt
* decklink
* hls ( for preview)
* webrtc ( for preview, planned)
* rtmp (planned)
* shoutcast (planned)
* ....


### Dependencies
Development happens on Debian bookworm, so currently the following versions are recommended.

* python (version 3.11)
* gst-interpipe ( develop branch )
* gstreamer1.0 (version 1.23)

there is no package for gst-interpipes in debian bookworm. follow the [compilation guide]() or look at (or use) the [Dockerfile](/Dockerfile)


### Getting Started

#### pipenv
@TODO

#### Docker
The easiest way for getting started is using the provided docker-compose.yml.
gstreamer and so DOVE, can use your GPU for decoding ( and encoding ).
Currently VAAPI is supported you can use the docker-compose.vaapi.yml to utilize it.

```
git clone https://github.com/dorftv/dove.git  && cd dove

# optional example config
# cp config-example.yml config.yml

docker compose up -d
```

point your Browser to [http://localhost:5000](http://localhost:5000)



