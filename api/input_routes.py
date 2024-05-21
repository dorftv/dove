from fastapi import APIRouter, Request, HTTPException
from api.websockets import manager
from pipeline_handler import PipelineHandler
from pipelines.description import Description
from pipelines.base import GSTBase
from api.input_models import InputDTO, SuccessDTO, InputDeleteDTO
from api.output_models import OutputDeleteDTO
from api.mixers_dtos import mixerRemoveDTO

from api.helper import get_routers
from api.helper import get_model_fields

router = APIRouter()

# Discover and include Routes for Inputs
for router_module, module_name in get_routers('api.inputs'):
    router.include_router(router_module, prefix="/inputs", tags=['Inputs'])

# List avalable Input Types
@router.get("/inputs/types", tags=['Inputs', 'Config'])
async def get_input_models():
    return get_model_fields('api.inputs',{'InputDTO'})

# List all Inputs
@router.get("/inputs", tags=['Inputs'])
async def get_all_inputs(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    inputs: list[Input] = handler._pipelines["inputs"] if handler._pipelines is not None else []
    descriptions: list[Description] = []

    for pipeline in inputs:
        descriptions.append(pipeline.describe())
    return descriptions

# Delete an Input
@router.delete("/inputs", response_model=SuccessDTO)
async def delete(request: Request, data: InputDeleteDTO):
    handler: "PipelineHandler" = request.app.state._state["pipeline_handler"]
    if handler.get_pipeline("inputs", data.uid) is not None:
        handler.delete_pipeline("inputs", data.uid)
        await manager.broadcast("DELETE", data)

        preview = handler.get_preview_pipeline(data.uid)
        if preview is not None:
            handler.delete_pipeline("outputs", preview.data.uid)
            await manager.broadcast("DELETE", data=(OutputDeleteDTO(uid=preview.data.uid)))

        mixers = handler.get_pipelines('mixers')
        for mixer in mixers:
            if mixer.data.type == "scene":
                while True:
                    mixerInput = mixer.data.getMixerInputDTObySource(data.uid)
                    if mixerInput is None:
                        break
                    mixer.remove_source(mixerRemoveDTO(src=data.uid, index=mixerInput.index))
    return SuccessDTO(uid=data.uid)

