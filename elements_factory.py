from uuid import uuid4
from logger import logger

from api.mixers_dtos import mixerDTO, sceneMixerDTO, mixerInputDTO, programMixerDTO, mixerCutDTO, mixerCutProgramDTO
from pipelines.mixers.scene_mixer import sceneMixer
from pipelines.mixers.program_mixer import programMixer
from api.outputs.hlssink2 import hlssink2OutputDTO
from pipelines.outputs.hlssink2 import hlssink2Output

from api.outputs.srtsink import srtsinkOutputDTO
from pipelines.outputs.srtsink import srtsinkOutput
from api.outputs.rtspclientsink import rtspclientsinkOutputDTO
from pipelines.outputs.rtspclientsink import rtspclientsinkOutput

from api.helper import get_dtos
from pipelines.helper import get_pipeline_classes

from config_handler import ConfigReader


config = ConfigReader()

input_dtos = {model_type: model for model, model_type in get_dtos('input')}
output_dtos = {model_type: model for model, model_type in get_dtos('output')}
input_pipeline_classes = {model_type: model for model, model_type in get_pipeline_classes('input')}
output_pipeline_classes = {model_type: model for model, model_type in get_pipeline_classes('output')}


class ElementsFactory:
    def __init__(self, handler):
        self.handler = handler
    scene_list = config.get_scenes()
    input_list = config.get_inputs()
    output_list = config.get_outputs()
    program_overlays_list = config.get_program_overlays()
    cutProgram = None

    # TODO  config.get_preview_enabled()
    preview_enabled = True


    def create_pipeline(self, io_type, name, data):
        data['name'] = data.get('name', name)
        dto_class = input_dtos.get(data['type']) if io_type == 'input' else output_dtos.get(data['type'])
        pipeline_class = input_pipeline_classes.get(data['type']) if io_type == 'input' else output_pipeline_classes.get(data['type'])

        if pipeline_class:
            if dto_class:
                dto_instance = dto_class(**data)
                new_pipeline = pipeline_class(data=dto_instance)
                self.handler.add_pipeline(new_pipeline)
                return new_pipeline
            else:
                logger.log(f"Could not find DTO class for {data['type']}", level='ERROR')
                return None
        else:
            logger.log(f"Could not find Pipeline class for {data['type']}", level='ERROR')
            return None

    def create_preview(self, type, uid):
        preview_config = config.get_preview_config(type)
        if preview_config['type'] == "hlssink2":
            previewOutput = hlssink2Output(data=hlssink2OutputDTO(
                src=uid,
                is_preview=True,
                ** preview_config
            ))
        elif preview_config['type'] == "srtsink":
            host, port, ingest_port = config.get_whep_proxy()

            previewOutput = srtsinkOutput(data=srtsinkOutputDTO(
                src=uid,
                is_preview=True,
                uri=f"srt://{host}:{ingest_port}?streamid=publish:{uid}&pkt_size=1316",
                ** preview_config
            ))
        elif preview_config['type'] == "rtspclientsink":
            host, port, ingest_port = config.get_whep_proxy()
            previewOutput = rtspclientsinkOutput(data=rtspclientsinkOutputDTO(
                src=uid,
                is_preview=True,
                location=f"rtsp://{ host }:{ ingest_port }/{uid}",
                ** preview_config
            ))
        self.handler.add_pipeline(previewOutput)

    def create_mixer(self, name, scene_details):
        mixerUuid = scene_details.get('uid', uuid4())
        mixerDTO = sceneMixerDTO(uid=mixerUuid, name=name, type="scene", n=scene_details.get('n', 0), locked=scene_details.get('locked', False), src_locked=scene_details.get('src_locked', False))
        mixer = sceneMixer(data=mixerDTO)
        self.handler.add_pipeline(mixer)
        self.create_preview('scenes', mixerUuid)
        return mixer

    async def create_pipelines(self):
        inputs = {}
        if True:
            programUuid = uuid4()
            programDTO = programMixerDTO(uid=programUuid, name="program", type="program")
            newProgramMixer = (programMixer(data=programDTO))
            self.handler.add_pipeline(newProgramMixer)
            self.create_preview('program', programUuid)

        if self.scene_list is not None:
            for scene_name in self.scene_list:
                scene_details = config.get_scene_details(scene_name)
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

                        if scene_details.get('program', False):
                            self.cutProgram = mixerCutProgramDTO(src=scene.data.uid)
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
                                pipeline = self.create_pipeline('input', name, input)
                                self.create_preview('inputs', pipeline.data.uid)
                                inputs[f"{scene_name}.{name}"] =  pipeline.data.uid
                            if pipeline is not None:
                                uid = pipeline.data.uid

                                scene.data.update_mixer_input(index, src=uid)
                                cutInput = mixerCutDTO(src=uid, target=scene.data.uid, index=index)
                                scene.add_source(cutInput)
                                scene.update_pad_from_sources("video", index)
                        index += 1
        program_index = 1
        if self.program_overlays_list is not None:
            for name, overlays in self.program_overlays_list.items():
                program_index +=1
                input = overlays.get('input', None)
                if input:
                    if isinstance(input, str):
                        pipeline =  self.handler.get_pipeline("inputs", inputs[str(input)])
                elif overlays.get('type', None) is not None:
                    pipeline = self.create_pipeline('input', name, overlays)

                if pipeline is not None:
                    uid = pipeline.data.uid
                    newProgramMixer.data.update_mixer_input(program_index, src=uid)
                    newProgramMixer.add_slot()
                    cutInput = mixerCutDTO(src=uid, target=newProgramMixer.data.uid, index=program_index)
                    newProgramMixer.add_source(cutInput)
                    newProgramMixer.update_pad_from_sources("video", program_index)


        if self.output_list is not None:
            for name, output in self.output_list.items():
                type = output.get('type')
                if type is not None:
                    output['name'] = output.get('name', name)
                    output['src'] = programUuid
                    self.create_pipeline('output', name, output)



        if self.input_list is not None:
            for name, input_details in self.input_list.items():
                inputUuid =  uuid4()
                pipeline = self.create_pipeline('input', name, input_details)
        if isinstance(self.cutProgram, mixerCutProgramDTO):
            newProgramMixer.cut_program(self.cutProgram)
