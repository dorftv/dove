from uuid import uuid4
import gi
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

gi.require_version('Gst', '1.0')

config = ConfigReader('/app/config.toml')


class ElementsFactory:
    mixer_list = config.get_mixers()
    preview_enabled = True  # config.get_preview_enabled()

    def create_pipelines(self):
        inputs = []
        outputs = []
        mixers = []

        for mixer, input_list in self.mixer_list.items():
            # print(f"Mixer: {mixer_list}")
            mixerUuid = uuid4()
            mixers.append(mixerMixer(data=mixerMixerDTO(uid=mixerUuid, type="mixer")))
            # if self.preview_enabled:
            # @TODO check if output
            outputs.append(previewHlsOutput(data=previewHlsOutputDTO(src=mixerUuid)))

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

                # if self.preview_enabled:
                # @TODO check if output
                outputs.append(previewHlsOutput(data=previewHlsOutputDTO(src=uuid)))
                # print(preview_enabled)
                pipelines = {"mixers": mixers, "inputs": inputs, "outputs": outputs}

        return pipelines

    def create_input(self):
        print("x")


if __name__ == "__main__":
    handler = HandlerSingleton()
    api = APIThread(pipeline_handler=handler)
    api.start()

    time.sleep(1)
    handler.start()
