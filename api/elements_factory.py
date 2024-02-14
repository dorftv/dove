from uuid import uuid4

from api.mixers_dtos import dynamicMixerDTO, mixerInputDTO
from pipelines.mixers.dynamic_mixer import dynamicMixer

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

    #RODO  config.get_preview_enabled()    
    preview_enabled = True  

    def create_input(self, type, name, input):
        uid = uuid4()
        if type == "testsrc":
            newInput = (
                TestInput(data=TestInputDTO(name=name, uid=uid, volume=input.get('volume', 0.8), pattern=input.get('pattern', 1), wave=input.get('wave', 4))))
        elif type == "urisrc":
            newInput = (
                UriInput(data=UriInputDTO(name=name, uid=uid, uri=input.get('uri', ''), loop=input.get('loop', False))))
        elif type == "wpesrc":
            newInput = (
                WpeInput(data=WpeInputDTO(name=name, uid=uid, uri=input.get('uri', ''))))
        elif type == "ytdlpsrc":
            newInput = (
                ytDlpInput(data=ytDlpInputDTO(name=name, uid=uid, uri=input.get('uri', ''), loop=input.get('loop', False))))
        self.handler.add_pipeline(newInput)
        return newInput


    async def create_pipelines(self):
        if self.mixer_list is not None:
            for mixer, mixer_details in self.mixer_list.items():
                mixerUuid = uuid4()
                newMixerDTO = dynamicMixerDTO(uid=mixerUuid, name=mixer, type="mixer")
                newMixer = dynamicMixer(data=newMixerDTO)                
                self.handler.add_pipeline(newMixer)

                previewOutput = (previewHlsOutput(data=previewHlsOutputDTO(src=mixerUuid)))
                self.handler.add_pipeline(previewOutput)

                # Add Inputs assigned to Mixers
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
                                # @TODO make props work
                                uid = pipeline.data.uid
                                mixerInput = mixerInputDTO(src=uid, xpos=input.get('xpos', 0), ypos=input.get('ypos', 0), width=input.get('width', None), height=input.get('height', None), alpha=input.get('alpha', 1), zorder=input.get('zorder', i), immutable=input.get('immutable', False))
                                newMixerDTO.add_input(mixerInput)
                                newMixer.overlay(mixerInput)                         
                                i += 1

                    # Add Outputs to Mixers
                    if 'inputs' in mixer_details:
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