import asyncio

import requests

from api.inputs_dtos import PlaylistInputDTO
from pipelines.inputs.input import Input

class PlaylistInput(Input):
    data: PlaylistInputDTO

    def _load_playlist(self, uri):
        try:
            r = requests.get(uri)
            if r.status_code == 200:
                return r.json()
            else:
                self.logger.error("Error loading playlist from http server!")
                return None
        except Exception:
            self.logger.error("Error loading playlist from http server!")
            return None

    async def html_stop_task(self):
        item = self.data.playlist[self.index]
        await asyncio.sleep(item.get("duration", 5))
        self._on_about_to_finish(self.playbin)

    def _setPlaybackItem(self, item):
        if item.get("type") == "html":
            self.playbin.set_property("uri", f"web+{item.get('uri')}")
            asyncio.run_coroutine_threadsafe(self.html_stop_task(), asyncio.get_event_loop())
        else:
            self.playbin.set_property("uri", item.get("uri"))

    def _jumpToNextPlaylist(self):
        data = self._load_playlist(self.next["uri"])
        if data is not None:
            self.data.playlist = data["playlist"]
            self.next = data.get("next")
            self.looping = data.get("looping", False)
        self.index = 0

    def build(self):
        # TODO: implement (we should think about if this class Architecture is still relevant with the new system)
        pass

    def __on_about_to_finish(self, playbin):
        self.index += 1

        if self.index >= len(self.data.playlist):
            if hasattr(self, "next") and self.next is not None:
                self._jumpToNextPlaylist()
            elif self.looping:
                self.index = 0

            self._setPlaybackItem(self.data.playlist[self.index])
