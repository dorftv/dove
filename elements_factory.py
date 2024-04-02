from uuid import uuid4
import time
from api.mixers_dtos import mixerDTO, sceneMixerDTO, mixerInputDTO, programMixerDTO, mixerCutDTO
from pipelines.mixers.scene_mixer import sceneMixer
from pipelines.mixers.program_mixer import programMixer

from api.inputs_dtos import InputDTO, TestInputDTO, UriInputDTO, WpeInputDTO, ytDlpInputDTO
from pipelines.inputs.test_input import TestInput
from pipelines.inputs.uri_input import UriInput
from pipelines.inputs.wpe_input import WpeInput
from pipelines.inputs.ytdlp_input import ytDlpInput

from api.outputs_dtos import OutputDTO, srtOutputDTO, decklinkOutputDTO, previewHlsOutputDTO
from pipelines.outputs.srt_output import srtOutput
from pipelines.outputs.decklink_output import decklinkOutput
from pipelines.outputs.preview_hls_output import previewHlsOutput

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
                TestInput(data=TestInputDTO(name=input.get('name',name), uid=uid, volume=input.get('volume', 0.8), pattern=input.get('pattern', 1), wave=input.get('wave', 4), preview=input.get('preview', True), locked=input.get('locked', False))))
        elif type == "urisrc":
            newInput = (
                UriInput(data=UriInputDTO(name=input.get('name',name), uid=uid, volume=input.get('volume', 0.8), uri=input.get('uri', ''), loop=input.get('loop', False),  preview=input.get('preview', True), locked=input.get('locked', False))))
        elif type == "wpesrc":
            newInput = (
                WpeInput(data=WpeInputDTO(name=input.get('name',name), uid=uid, location=input.get('location'), draw_background=input.get('draw_background', True), preview=input.get('preview', True), locked=input.get('locked', False))))
        elif type == "ytdlpsrc":
            newInput = (
                ytDlpInput(data=ytDlpInputDTO(name=input.get('name',name), uid=uid, volume=input.get('volume', 0.8), uri=input.get('uri', ''), loop=input.get('loop', False),  preview=input.get('preview', True), locked=input.get('locked', False))))
        self.handler.add_pipeline(newInput)
        return newInput

    def create_mixer(self, name, scene_details):
        mixerUuid = uuid4()
        mixerDTO = sceneMixerDTO(uid=mixerUuid, name=name, type="scene", n=scene_details.get('n', 0), locked=scene_details.get('locked', False), src_locked=scene_details.get('src_locked', False))
        mixer = sceneMixer(data=mixerDTO)
        self.handler.add_pipeline(mixer)
        previewOutput = previewHlsOutput(data=previewHlsOutputDTO(src=mixerUuid))
        self.handler.add_pipeline(previewOutput)
        return mixer

    async def create_pipelines(self):
        inputs = {}
        if True:
            programUuid = uuid4()
            programDTO = programMixerDTO(uid=programUuid, name="program", type="program")
            programwMixer = programMixer(data=programDTO)
            self.handler.add_pipeline(programwMixer)
            programPreviewOutput = previewHlsOutput(data=previewHlsOutputDTO(src=programUuid))
            self.handler.add_pipeline(programPreviewOutput)


        if self.scene_list is not None:
            for scene_name in self.scene_list:
                print(scene_name)
                scene_details = config.get_scene_details(scene_name)
                #print(scene_details)

                scene_pads = config.get_scene_inputs(scene_name)
                #print(scene_pads)
                n = scene_details.get('n', 0)
                if scene_pads is not None:
                    s = len(scene_pads)
                    if s > n:
                        scene_details["n"] = s
                scene = self.create_mixer(scene_details.get('name', scene_name), scene_details)


                if scene_pads is not None:
                    i = 0
                    for name, details in scene_pads.items():
                        if details.get("name", None) is None:
                            details["name"] = name

                        if details.get("sink", None) is None:
                            i += 1
                            sink = f"sink_{i}"
                        else:
                            sink = details.get("sink")
                        properties = ['alpha', 'xpos', 'ypos', 'width', 'height', 'zorder', 'volume', 'locked', 'src_locked', 'mute', 'preview', 'name']
                        for prop in properties:
                            value = details.get(prop)
                            if value is not None:
                                scene.data.update_mixer_input(sink ,  **{prop: value})
                        scene.update_pad_from_sources("video", sink)

                        input = details.get('input', None)
                        if input:

                            if isinstance(input, str):
                                pipeline =  self.handler.get_pipeline("inputs", inputs[input])
                            elif input.get('type', None) is not None:
                                pipeline = self.create_input(input.get('type'), name, input)
                                inputs[name] =  pipeline.data.uid
                            if pipeline is not None:
                                uid = pipeline.data.uid
                                # @TODO without this audio is distorted. find a better way.
                                #time.sleep(0.3)
                                scene.data.update_mixer_input(sink, src=uid)
                                cutInput = mixerCutDTO(src=uid, target=scene.data.uid, sink=sink)
                                scene.add_source(cutInput)
        if self.output_list is not None:
            for name, output in self.output_list.items():
                type = output.get('type')
                if type is not None:
                    uid = uuid4()
                    if type == "srtsink":
                        newOutput = (
                            srtOutput(data = srtOutputDTO(uid=uid, src=programUuid, uri=output.get('uri', None), streamid=output.get('streamid', None), locked=output.get('locked', False))))
                    if type == "decklinksink":
                        newOutput = (
                            decklinkOutput(data=srtOutputDTO(src=programUuid, device=output.get('device', None), mode=output.get('mode', None), interlaced=output.get('interlaced', False), locked=output.get('locked', False))))
                    if newOutput is not None:
                        self.handler.add_pipeline(newOutput)

        if self.input_list is not None:
            for name, input_details in self.input_list.items():
                inputUuid =  uuid4()
                pipeline = self.create_input(input_details['type'], name, input_details)
