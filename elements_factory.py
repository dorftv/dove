from uuid import uuid4
from logger import logger
from api.mixers_dtos import mixerDTO, sceneMixerDTO, mixerInputDTO, programMixerDTO, mixerCutProgramDTO
from pipelines.mixers.scene_mixer import sceneMixer
from pipelines.mixers.program_mixer import programMixer
from api.helper import get_dtos
from api.input_models import AudioFilterDTO
from pipelines.helper import get_pipeline_classes

from config_handler import ConfigReader


config = ConfigReader()

input_dtos = {model_type: model for model, model_type in get_dtos('input')}
output_dtos = {model_type: model for model, model_type in get_dtos('output')}
input_pipeline_classes = {model_type: model for model, model_type in get_pipeline_classes('input')}
output_pipeline_classes = {model_type: model for model, model_type in get_pipeline_classes('output')}

SLOT_PROPERTIES = ['alpha', 'xpos', 'ypos', 'width', 'height', 'zorder', 'volume', 'locked', 'src_locked', 'mute', 'name']


class ElementsFactory:
    def __init__(self, handler):
        self.handler = handler
        self.cutProgram = None
        self.scene_list = config.get_scenes()
        self.input_list = config.get_inputs()
        self.output_list = config.get_outputs()
        self.encoder_list = config.get_encoders()
        self.program_overlays_list = config.get_program_overlays()

    def create_pipeline(self, io_type, name, data):
        data['name'] = data.get('name', name)
        dtos = input_dtos if io_type == 'input' else output_dtos
        classes = input_pipeline_classes if io_type == 'input' else output_pipeline_classes

        dto_class = dtos.get(data['type'])
        pipeline_class = classes.get(data['type'])

        if not pipeline_class:
            logger.log(f"No pipeline class for {data['type']}", level='ERROR')
            return None
        if not dto_class:
            logger.log(f"No DTO class for {data['type']}", level='ERROR')
            return None

        dto_instance = dto_class(**data)
        new_pipeline = pipeline_class(data=dto_instance)
        self.handler.add_pipeline(new_pipeline)
        return new_pipeline

    def create_mixer(self, name, scene_details):
        mixer_uid = scene_details.get('uid', uuid4())
        dto = sceneMixerDTO(
            uid=mixer_uid, name=name, type="scene",
            n=scene_details.get('n', 0),
            locked=scene_details.get('locked', False),
            src_locked=scene_details.get('src_locked', False),
        )
        mixer = sceneMixer(data=dto)
        self.handler.add_pipeline(mixer)
        return mixer

    def _create_program_mixer(self):
        program_uid = uuid4()
        dto = programMixerDTO(uid=program_uid, name="program", type="program")
        mixer = programMixer(data=dto)
        self.handler.add_pipeline(mixer)
        return mixer, program_uid

    def _build_steps(self):
        """Build an ordered list of (description, callable) steps for pipeline creation.

        Order: create all entities first, then link slots, then cut program.
        """
        steps = []
        inputs_map = {}
        link_steps = []

        # 1. Program mixer
        state = {}
        def create_program():
            mixer, uid = self._create_program_mixer()
            state['program_mixer'] = mixer
            state['program_uid'] = uid
        steps.append(("program mixer", create_program))

        # 2. Scenes: create mixers and inputs (no linking yet)
        if self.scene_list:
            for scene_name in self.scene_list:
                scene_details = config.get_scene_details(scene_name)
                scene_slots = config.get_scene_inputs(scene_name)

                n = scene_details.get('n', 0)
                if scene_slots and len(scene_slots) > n:
                    scene_details["n"] = len(scene_slots)

                sn = scene_name
                sd = scene_details
                def create_scene(sn=sn, sd=sd):
                    scene = self.create_mixer(sd.get('name', sn), sd)
                    state[f'scene_{sn}'] = scene
                    if sd.get('program', False):
                        self.cutProgram = mixerCutProgramDTO(src=scene.data.uid)
                steps.append((f"scene {sn}", create_scene))

                if scene_slots:
                    for index, (slot_name, details) in enumerate(scene_slots.items()):
                        idx = index
                        sn_ = sn
                        sl_name = slot_name
                        sl_details = details

                        # Create input (if inline dict)
                        input_ref = details.get('input')
                        if isinstance(input_ref, dict) and input_ref.get('type'):
                            def create_slot_input(sn_=sn_, sl_name=sl_name, sl_details=sl_details, idx=idx):
                                scene = state[f'scene_{sn_}']
                                if sl_details.get("name") is None:
                                    sl_details["name"] = sl_name
                                for prop in SLOT_PROPERTIES:
                                    value = sl_details.get(prop)
                                    if value is not None:
                                        scene.data.update_mixer_input(idx, **{prop: value})
                                pipeline = self.create_pipeline('input', sl_name, sl_details['input'])
                                if pipeline:
                                    inputs_map[f"{sn_}.{sl_name}"] = pipeline.data.uid
                            steps.append((f"input {sn}.{slot_name}", create_slot_input))

                        # Defer linking to after all entities exist
                        def link_slot(idx=idx, sn_=sn_, sl_name=sl_name, sl_details=sl_details):
                            scene = state[f'scene_{sn_}']
                            scope_key = f"{sn_}.{sl_name}"
                            input_ref = sl_details.get('input')

                            uid = None
                            if isinstance(input_ref, dict):
                                uid = inputs_map.get(scope_key)
                            elif isinstance(input_ref, str):
                                uid = inputs_map.get(input_ref)

                            if uid:
                                scene.data.update_mixer_input(idx, src=uid)
                                scene.link_source(idx, uid)
                        link_steps.append((f"link {sn}.{slot_name}", link_slot))

        # 3. Program overlays: create inputs first, link later
        if self.program_overlays_list:
            program_index = 1
            for name, overlays in self.program_overlays_list.items():
                program_index += 1
                ov_name = name
                ov_data = overlays
                pi = program_index

                input_ref = overlays.get('input')
                if isinstance(input_ref, dict) and input_ref.get('type'):
                    def create_ov_input(ov_name=ov_name, ov_data=ov_data):
                        pipeline = self.create_pipeline('input', ov_name, ov_data['input'])
                        if pipeline:
                            inputs_map[f"program.{ov_name}"] = pipeline.data.uid
                    steps.append((f"input overlay {ov_name}", create_ov_input))
                elif not input_ref and overlays.get('type') is not None:
                    def create_ov_direct(ov_name=ov_name, ov_data=ov_data):
                        pipeline = self.create_pipeline('input', ov_name, ov_data)
                        if pipeline:
                            inputs_map[f"program.{ov_name}"] = pipeline.data.uid
                    steps.append((f"input overlay {ov_name}", create_ov_direct))

                def link_overlay(ov_name=ov_name, pi=pi):
                    program_mixer = state['program_mixer']
                    uid = inputs_map.get(f"program.{ov_name}")
                    if uid:
                        # Ensure slot exists for overlay index
                        while len(program_mixer.data.sources) <= pi:
                            program_mixer.add_slot()
                        program_mixer.data.update_mixer_input(pi, src=uid)
                        program_mixer.link_source(pi, uid)
                link_steps.append((f"link overlay {ov_name}", link_overlay))

        # 4. Encoders (before outputs so outputs can reference them)
        encoder_map = {}  # config name → UUID
        if self.encoder_list:
            for enc_name, enc_conf in self.encoder_list.items():
                e_name = enc_name
                e_conf = enc_conf
                def create_encoder(e_name=e_name, e_conf=e_conf):
                    from pipelines.encoders.encoder import Encoder
                    from api.encoder_models import EncoderEntityDTO
                    raw_filters = e_conf.get('audio_filters', [])
                    audio_filters = [AudioFilterDTO(**f) for f in raw_filters] if raw_filters else []
                    entity = Encoder(data=EncoderEntityDTO(
                        name=e_conf.get('name', e_name),
                        type=e_conf.get('type', 'video'),
                        element=e_conf.get('element', ''),
                        codec=e_conf.get('codec', ''),
                        options=e_conf.get('options', ''),
                        profile=e_conf.get('profile'),
                        width=e_conf.get('width'),
                        height=e_conf.get('height'),
                        framerate=e_conf.get('framerate'),
                        src=state['program_uid'],
                        audio_filters=audio_filters,
                    ))
                    self.handler.add_pipeline(entity)
                    encoder_map[e_name] = entity.data.uid
                steps.append((f"encoder {enc_name}", create_encoder))

        # 5. Standalone inputs
        if self.input_list:
            for name, input_details in self.input_list.items():
                in_name = name
                in_details = input_details
                def create_input(in_name=in_name, in_details=in_details):
                    self.create_pipeline('input', in_name, in_details)
                steps.append((f"input {name}", create_input))

        # 6. Outputs
        if self.output_list:
            for name, output_conf in self.output_list.items():
                out_name = name
                out_conf = output_conf
                def create_output(out_name=out_name, out_conf=out_conf):
                    output_type = out_conf.get('type')
                    if output_type:
                        out_conf['name'] = out_conf.get('name', out_name)
                        out_conf['src'] = state['program_uid']
                        # Resolve encoder name references to UUIDs
                        for enc_key in ('video_encoder', 'audio_encoder'):
                            ref = out_conf.get(enc_key)
                            if isinstance(ref, str) and ref in encoder_map:
                                out_conf[enc_key] = encoder_map[ref]
                        self.create_pipeline('output', out_name, out_conf)
                steps.append((f"output {name}", create_output))

        # 7. Link all slots and overlays
        steps.extend(link_steps)

        # 8. Cut program (last)
        def cut_program():
            if isinstance(self.cutProgram, mixerCutProgramDTO):
                state['program_mixer'].cut_program_sync(self.cutProgram)
        steps.append(("cut program", cut_program))

        return steps

    def create_pipelines(self):
        steps = self._build_steps()
        for desc, fn in steps:
            logger.log(f"Factory: creating {desc}", level='DEBUG')
            fn()
        logger.log("Factory: all pipelines created", level='DEBUG')
