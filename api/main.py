from uuid import uuid4
import gi
gi.require_version('Gst', '1.0')

import time
from config_handler import ConfigReader

from api.inputs_dtos import InputDTO, TestInputDTO, UriInputDTO, WpeInputDTO, ytDlpInputDTO
from api.mixers_dtos import mixerMixerDTO
from api.outputs_dtos import previewHlsOutputDTO
from pipelines.inputs.test_input import TestInput
from pipelines.inputs.uri_input import UriInput
from pipelines.inputs.wpe_input import WpeInput
from pipelines.inputs.ytdlp_input import ytDlpInput
from pipelines.mixers.mixer_mixer import mixerMixer
from pipelines.outputs.preview_hls_output import previewHlsOutput

from api_thread import APIThread
from pipeline_handler import HandlerSingleton


config = ConfigReader()




class ElementsFactory:
    mixer_list = config.get_mixers()
    #RODO  config.get_preview_enabled()    
    preview_enabled = True  

    def create_pipelines(self):
        inputs = []
        mixers = []
        preview_outputs = []

        uid_dict = {}

        #@TODO add standalone Inputs and Outputs
        if self.mixer_list is not None:
            for mixer, input_list in self.mixer_list.items():
                mixerUuid = uuid4()
                mixers.append(mixerMixer(data=mixerMixerDTO(uid=mixerUuid, type="mixer")))
                preview_outputs.append(previewHlsOutput(data=previewHlsOutputDTO(src=mixerUuid)))

                for name, details in input_list.items():
                    type = details['type']
                    uuid = uuid4()

                    if type == "testsrc":
                        inputs.append(
                            TestInput(data=TestInputDTO(name=name, uid=uuid, volume=details.get('volume', 0.8), pattern=1)))
                    elif type == "urisrc":
                        inputs.append(UriInput(data=UriInputDTO(name=name, uid=uuid, uri=details.get('uri', None),
                                                                loop=details.get('loop', None))))
                    elif type == "wpesrc":
                        inputs.append(WpeInput(data=WpeInputDTO(name=name, uid=uuid, volume=1.0, pattern=1)))
                    elif type == "ytdlpsrc":
                        inputs.append(ytDlpInput(data=ytDlpInputDTO(name=name, uid=uuid, uri=details.get('uri', None))))

        pipelines = {"mixers": mixers, "inputs": inputs, "outputs": preview_outputs}
        return pipelines


if __name__ == "__main__":
    handler = HandlerSingleton()
    api = APIThread(pipeline_handler=handler)
    api.start()
    
    handler.start()
