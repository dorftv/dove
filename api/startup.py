from config_handler import ConfigReader  # make sure to replace with your actual module name
from api.inputs_dtos import InputDTO, SuccessDTO, InputDeleteDTO, TestInputDTO, UriInputDTO, WpeInputDTO, ytDlpInputDTO
from api.outputs_dtos import OutputDTO, SuccessDTO, OutputDeleteDTO, previewHlsOutputDTO

from uuid import uuid4
from pipelines.inputs.test_input import TestInput
from pipelines.inputs.uri_input import UriInput
from pipelines.inputs.wpe_input import WpeInput
from pipelines.inputs.ytdlp_input import ytDlpInput
from pipelines.outputs.preview_hls_output import previewHlsOutput

config = ConfigReader('/app/config.toml')


class createElements():
    mixers = config.get_mixers()
    preview_enabled = True # config.get_preview_enabled()

    def create_mixer(self):
        input = []
        output = []
        for mixer, inputs in self.mixers.items():
            print(f"Mixer: {mixer}")    
            for name, details in inputs.items():  
                type = details['type']
                uuid = uuid4()
                if type == "testsrc":
                    input.append(TestInput(uid=uuid, data=TestInputDTO(name=name, uid=uuid, volume=details.get('volume', 0.8), pattern=1)))
                elif type == "urisrc":
                    input.append(UriInput(uid=uuid, data=UriInputDTO(name=name, uid=uuid,  uri=details.get('uri', None), loop=details.get('loop', None))))
                elif type == "wpesrc":
                    input.append(WpeInput(uid=uuid, data=WpeInputDTO(name=name, uid=uuid, volume=1.0, pattern=1)))
                elif type == "ytdlpsrc":
                    input.append(ytDlpInput(uid=uuid, data=ytDlpInputDTO(name=name, uid=uuid, volume=1.0, pattern=1)))
        
                #if self.preview_enabled:
                output.append(previewHlsOutput(uid=uuid4(), src=uuid, data=previewHlsOutputDTO(src=uuid)))
                #print(preview_enabled)
                pipelines = {"inputs": input, "outputs": output}

        return pipelines

    def create_input():
        print("x")

# Loop over the outer dictionary
    

    # Loop over the inner dictionary
