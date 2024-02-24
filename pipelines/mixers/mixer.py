from logger import logger
from api.mixers_dtos import mixerCutDTO, mixerInputsDTO, mixerInputDTO, mixerDTO
from pipelines.base import GSTBase
from abc import ABC
from gi.repository import Gst, GLib
from api.websockets import manager
import asyncio
from uuid import UUID, uuid4



class Mixer(GSTBase, ABC):

    data: mixerDTO
    
    def get_video_end(self) -> str:
        return f" queue ! interpipesink name=video_{self.data.uid} async=false sync=true "

    def get_audio_end(self):
        return f" queue ! interpipesink name=audio_{self.data.uid} async=false sync=true "

    def getMixer(self, audio_or_video):
        mixerpipe = self.get_pipeline()
        mixer = mixerpipe.get_by_name(f"{audio_or_video}mixer_{ self.data.uid}")
        return mixer