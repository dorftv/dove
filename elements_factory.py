from uuid import uuid4
import time
from api.mixers_dtos import mixerDTO, sceneMixerDTO, mixerInputDTO, programMixerDTO, mixerCutDTO
from pipelines.mixers.scene_mixer import sceneMixer
from pipelines.mixers.program_mixer import programMixer
from api.input_models import InputDTO

from api.inputs.testsrc import  TestsrcInputDTO
from pipelines.inputs.testsrc import TestsrcInput

from api.inputs.playbin3 import  Playbin3InputDTO
from pipelines.inputs.playbin3 import Playbin3Input

from api.inputs.wpesrc import  WpesrcInputDTO
from pipelines.inputs.wpesrc import WpesrcInput

from api.inputs.ytdlp import YtdlpInputDTO
from pipelines.inputs.ytdlp import YtdlpInput

from api.output_models import OutputDTO, PreviewHlsOutputDTO
from pipelines.outputs.preview_hls import PreviewHlsOutput

from pipelines.outputs.srtsink import SrtsinkOutput
from api.outputs.srtsink import SrtsinkOutputDTO

from api.outputs.decklink import DecklinkOutputDTO
from pipelines.outputs.decklink import DecklinkOutput

from pipelines.outputs.shout2send import Shout2sendOutput
from api.outputs.shout2send import Shout2sendOutputDTO




from config_handler import ConfigReader
config = ConfigReader()


class ElementsFactory:
    def __init__(self, handler):
        self.handler = handler
    scene_list = config.get_scenes()
    input_list = config.get_inputs()
    output_list = config.get_outputs()

    # TODO  config.get_preview_enabled()
    preview_enabled = True

    def create_input(self, type, name, input):
        uid = uuid4()
        if type == "testsrc":
            newInput = (
                TestsrcInput(data=TestsrcInputDTO(name=input.get('name',name), uid=uid, volume=input.get('volume', 0.8), pattern=input.get('pattern', 1), wave=input.get('wave', 4), preview=input.get('preview', True), locked=input.get('locked', False))))
        elif type == "playbin3":
            newInput = (
                Playbin3Input(data=Playbin3InputDTO(name=input.get('name',name), uid=uid, volume=input.get('volume', 0.8), uri=input.get('uri', ''), loop=input.get('loop', False),  preview=input.get('preview', True), locked=input.get('locked', False))))
        elif type == "wpesrc":
            newInput = (
                WpesrcInput(data=WpesrcInputDTO(name=input.get('name',name), uid=uid, location=input.get('location'), draw_background=input.get('draw_background', True), preview=input.get('preview', True), locked=input.get('locked', False))))
        elif type == "ytdlp":
            newInput = (
                YtdlpInput(data=YtdlpInputDTO(name=input.get('name',name), uid=uid, volume=input.get('volume', 0.8), uri=input.get('uri', ''), loop=input.get('loop', False),  preview=input.get('preview', True), locked=input.get('locked', False))))
        if newInput is not None:
            self.handler.add_pipeline(newInput)
            return newInput
        else:
            return None

    def create_mixer(self, name, scene_details):
        mixerUuid = uuid4()
        mixerDTO = sceneMixerDTO(uid=mixerUuid, name=name, type="scene", n=scene_details.get('n', 0), locked=scene_details.get('locked', False), src_locked=scene_details.get('src_locked', False))
        mixer = sceneMixer(data=mixerDTO)
        self.handler.add_pipeline(mixer)
        previewOutput = PreviewHlsOutput(data=PreviewHlsOutputDTO(src=mixerUuid))
        self.handler.add_pipeline(previewOutput)
        return mixer

    async def create_pipelines(self):
        inputs = {}
        if True:
            programUuid = uuid4()
            programDTO = programMixerDTO(uid=programUuid, name="program", type="program")
            programwMixer = programMixer(data=programDTO)
            self.handler.add_pipeline(programwMixer)
            programPreviewOutput = PreviewHlsOutput(data=PreviewHlsOutputDTO(src=programUuid))
            self.handler.add_pipeline(programPreviewOutput)


        if self.scene_list is not None:
            for scene_name in self.scene_list:
                scene_details = config.get_scene_details(scene_name)
                #print(scene_details)

                scene_slots = config.get_scene_inputs(scene_name)

                n = scene_details.get('n', 0)
                if scene_slots is not None:
                    s = len(scene_slots)
                    if s > n:
                        scene_details["n"] = s
                scene = self.create_mixer(scene_details.get('name', scene_name), scene_details)

                index = 0
                if scene_slots is not None:
                    for name, details in scene_slots.items():
                        if details.get("name", None) is None:
                            details["name"] = name

                        properties = ['alpha', 'xpos', 'ypos', 'width', 'height', 'zorder', 'volume', 'locked', 'src_locked', 'mute', 'preview', 'name']
                        for prop in properties:
                            value = details.get(prop)
                            if value is not None:
                                scene.data.update_mixer_input(index ,  **{prop: value})

                        input = details.get('input', None)
                        if input:

                            if isinstance(input, str):
                                pipeline =  self.handler.get_pipeline("inputs", inputs[str(input)])
                            elif input.get('type', None) is not None:
                                pipeline = self.create_input(input.get('type'), name, input)
                                inputs[f"{scene_name}.{name}"] =  pipeline.data.uid
                            if pipeline is not None:
                                uid = pipeline.data.uid
                                # @TODO without this audio is distorted. find a better way.
                                #time.sleep(0.3)
                                scene.data.update_mixer_input(index, src=uid)
                                cutInput = mixerCutDTO(src=uid, target=scene.data.uid, index=index)
                                scene.add_source(cutInput)
                                scene.update_pad_from_sources("video", index)
                        index += 1


        if self.output_list is not None:
            for name, output in self.output_list.items():
                type = output.get('type')
                newOutput = None
                if type is not None:

                    uid = uuid4()
                    if type == "srtsink":
                        newOutput = (
                            SrtsinkOutput(data= SrtsinkOutputDTO(uid=uid, src=programUuid, uri=output.get('uri', None), streamid=output.get('streamid', None), locked=output.get('locked', False))))
                    if type == "decklink":
                        newOutput = (
                            DecklinkOutput(data=DecklinkOutputDTO(src=programUuid, device=output.get('device', None), mode=output.get('mode', None), interlaced=output.get('interlaced', False), locked=output.get('locked', False))))
                    if type == "shout2send":
                        newOutput = (
                            Shout2sendOutput(data=Shout2sendOutputDTO(src=programUuid, ip=output.get('ip', None), port=output.get('port', None), mount=output.get('mount', None), codec=output.get('codec', None),username=output.get('username', None),  password=output.get('password', None),  locked=output.get('locked', False))))
                    if newOutput is not None:
                        self.handler.add_pipeline(newOutput)

        if self.input_list is not None:
            for name, input_details in self.input_list.items():
                inputUuid =  uuid4()
                pipeline = self.create_input(input_details['type'], name, input_details)
