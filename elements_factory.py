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
    mixer_list = config.get_mixers()
    input_list = config.get_inputs()

    # TODO  config.get_preview_enabled()
    preview_enabled = True  

    def create_input(self, type, name, input):
        uid = uuid4()
        if type == "testsrc":
            newInput = (
                TestInput(data=TestInputDTO(name=name, uid=uid, volume=input.get('volume', 0.8), pattern=input.get('pattern', 1), wave=input.get('wave', 4))))
        elif type == "urisrc":
            newInput = (
                UriInput(data=UriInputDTO(name=name, uid=uid, volume=input.get('volume', 0.8), uri=input.get('uri', ''), loop=input.get('loop', False))))
        elif type == "wpesrc":
            newInput = (
                WpeInput(data=WpeInputDTO(name=name, uid=uid, location=input.get('location'), draw_background=input.get('draw_background', True))))
        elif type == "ytdlpsrc":
            newInput = (
                ytDlpInput(data=ytDlpInputDTO(name=name, uid=uid, volume=input.get('volume', 0.8), uri=input.get('uri', ''), loop=input.get('loop', False))))
        self.handler.add_pipeline(newInput)
        return newInput

    def create_mixer(self, name, mixer_details):
        mixerUuid = uuid4()        
        mixerDTO = sceneMixerDTO(uid=mixerUuid, name=name, type="scene", n=mixer_details.get('n', 0), locked=mixer_details.get('locked', False))
        mixer = sceneMixer(data=mixerDTO)
        self.handler.add_pipeline(mixer)
        previewOutput = previewHlsOutput(data=previewHlsOutputDTO(src=mixerUuid))
        self.handler.add_pipeline(previewOutput)        
        return mixer

    async def create_pipelines(self):
        if self.mixer_list is not None:
            for mixer, mixer_details in self.mixer_list.items():
                mixer_type = mixer_details.get('type')
                n = mixer_details.get('n', 0)
                s = len(mixer_details.get('inputs'))
                if s > n:
                    mixer_details["n"] = s
                
                mixer = self.create_mixer(mixer, mixer_details)

                if 'inputs' in mixer_details:
                    i = 0
                    inputs = mixer_details.get('inputs')
                    if inputs is not None:
                        for name, input in mixer_details['inputs'].items():
                            type = input.get('type')

                            if type is not None:
                                pipeline = self.create_input(type, name, input)
                            else:
                                pipeline = await self.handler.get_pipeline_by_name("inputs", name)
                            if pipeline is not None:
                                uid = pipeline.data.uid

                            i += 1
                            sink = f"sink_{i}"
                            if input.get("sink") is not None:
                                sink = input.get("sink")

                            properties = ['alpha', 'xpos', 'ypos', 'width', 'height', 'zorder', 'volume', 'locked', 'src_locked', 'mute']
                            for prop in properties:
                                if input.get(prop):
                                    mixer.data.update_mixer_input(sink ,  **{prop: input.get(prop)})

                            if pipeline is not None:
                                uid = pipeline.data.uid
                                # @TODO without this audio is distorted. find a better way.
                                time.sleep(0.3)
                                mixer.data.update_mixer_input(sink, src=uid)
                                cutInput = mixerCutDTO(src=uid, target=mixer.data.uid, sink=sink)
                                mixer.add_source(cutInput)

                    if 'outputs' in mixer_details:
                        outputs = mixer_details.get('outputs')
                        if outputs is not None:
                            for name, output in mixer_details['outputs'].items():
                                type = output.get('type')
                                if type is not None:
                                    uid = uuid4()
                                    if type == "srtsink":
                                        newOutput = (
                                            srtOutput(data = srtOutputDTO(src=mixerUuid, uri=output.get('uri', None), streamid=output.get('streamid', None))))
                                    if type == "decklinksink":
                                        newOutput = (
                                            srtOutput(data=srtOutputDTO(src=mixerUuid, device=output.get('device', None), mode=output.get('mode', None), interlaced=output.get('interlaced', False))))
                                    self.handler.add_pipeline(newOutput)


        if self.input_list is not None:
            for name, input_details in self.input_list.items():
                inputUuid =  uuid4()
                pipeline = self.create_input(input_details['type'], name, input_details)


        if True:
            programUuid = uuid4()
            programDTO = programMixerDTO(uid=programUuid, name="program", type="program")
            programwMixer = programMixer(data=programDTO) 
            self.handler.add_pipeline(programwMixer)
            programPreviewOutput = previewHlsOutput(data=previewHlsOutputDTO(src=programUuid))
            self.handler.add_pipeline(programPreviewOutput)

