from config_handler import ConfigReader  # make sure to replace with your actual module name
from api.inputs_dtos import InputDTO, SuccessDTO, InputDeleteDTO, TestInputDTO, UriInputDTO, WpeInputDTO, ytDlpInputDTO
from api.outputs_dtos import OutputDTO, SuccessDTO, OutputDeleteDTO, previewHlsOutputDTO
from api.mixers_dtos import mixerCutDTO, mixerInputsDTO, mixerInputDTO, mixerDTO, mixerMixerDTO

from uuid import uuid4
from pipelines.inputs.test_input import TestInput
from pipelines.inputs.uri_input import UriInput
from pipelines.inputs.wpe_input import WpeInput
from pipelines.inputs.ytdlp_input import ytDlpInput
from pipelines.outputs.preview_hls_output import previewHlsOutput
from pipelines.mixers.mixer_mixer import mixerMixer


config = ConfigReader('/app/config.toml')


class createElements():
    mixer_list = config.get_mixers()
    preview_enabled = True # config.get_preview_enabled()

    def create_mixer(self):
        inputs = []
        outputs = []
        mixers = []

        for mixer, input_list in self.mixer_list.items():
            #print(f"Mixer: {mixer_list}")
            mixerUuid = uuid4()
            mixers.append(mixerMixer(data=mixerMixerDTO(uid=mixerUuid, type="mixer")))
            #if self.preview_enabled:
            # @TODO check if output
            outputs.append(previewHlsOutput(data=previewHlsOutputDTO(src=mixerUuid)))

            for name, details in input_list.items():  
                type = details['type']
                uuid = uuid4()
                if type == "testsrc":
                    inputs.append(TestInput(data=TestInputDTO(name=name, uid=uuid, volume=details.get('volume', 0.8), pattern=1)))
                elif type == "urisrc":
                    inputs.append(UriInput(data=UriInputDTO(name=name, uid=uuid,  uri=details.get('uri', None), loop=details.get('loop', None))))
                elif type == "wpesrc":
                    inputs.append(WpeInput(data=WpeInputDTO(name=name, uid=uuid, volume=1.0, pattern=1)))
                elif type == "ytdlpsrc":
                    inputs.append(ytDlpInput(data=ytDlpInputDTO(name=name, uid=uuid, uri=details.get('uri', None))))
        
                #if self.preview_enabled:
                # @TODO check if output
                outputs.append(previewHlsOutput(data=previewHlsOutputDTO(src=uuid)))
                #print(preview_enabled)
                pipelines = {"mixers": mixers, "inputs": inputs, "outputs": outputs}

        return pipelines

    def create_input():
        print("x")

# Loop over the outer dictionary
    

    # Loop over the inner dictionary
