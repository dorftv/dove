from fastapi import APIRouter, Request, HTTPException
from pipeline_handler import PipelineHandler

from pipelines.base import GSTBase
from api.input_models import SuccessDTO, InputDeleteDTO, updateInputDTO
from api.mixers_dtos import mixerRemoveDTO
from api.auth import require_role, require_read

from api.helper import get_routers
from api.helper import get_model_fields

router = APIRouter()

# Discover and include Routes for Inputs (PUT creates input → dove-user)
for router_module, module_name in get_routers('api.inputs'):
    router.include_router(router_module, prefix="/inputs", tags=['Inputs'],
                          dependencies=[require_role("user")])

# List avalable Input Types
@router.get("/inputs/types", tags=['Inputs', 'Config'], dependencies=[require_read()])
async def get_input_models():
    return get_model_fields('api.inputs',{'InputDTO'})

# List all Inputs
@router.get("/inputs", tags=['Inputs'], dependencies=[require_read()])
async def get_all_inputs(request: Request):
    handler: GSTBase = request.app.state.pipeline_handler
    inputs: list[Input] = handler._pipelines["inputs"] if handler._pipelines is not None else []
    descriptions = []

    for pipeline in inputs:
        descriptions.append(pipeline.describe())
    return descriptions

# Delete an Input
@router.delete("/inputs", response_model=SuccessDTO, dependencies=[require_role("user")])
async def delete(request: Request, data: InputDeleteDTO):
    handler: "PipelineHandler" = request.app.state.pipeline_handler
    pipeline = handler.get_pipeline("inputs", data.uid)
    if pipeline is not None:
        if getattr(pipeline.data, 'locked', False):
            raise HTTPException(status_code=403, detail="Input is locked")
        # delete_pipeline handles preview cleanup + mixer unlinking + DELETE broadcasts
        handler.delete_pipeline("inputs", data.uid)

        # Also remove source references from mixer DTOs
        mixers = handler.get_pipelines('mixers')
        for mixer in mixers:
            if mixer.data.type == "scene":
                while True:
                    mixerInput = mixer.data.getMixerInputDTObySource(data.uid)
                    if mixerInput is None:
                        break
                    mixer.remove_source(mixerRemoveDTO(src=data.uid, index=mixerInput.index))
    return SuccessDTO(uid=data.uid)

@router.put("/inputs", response_model=SuccessDTO, dependencies=[require_role("user")])
async def update_input(request: Request,data: updateInputDTO):
    handler: GSTBase = request.app.state.pipeline_handler
    existing_input = handler.get_pipeline("inputs", data.uid)

    if existing_input:
        updated_input = await existing_input.update(data)
        return SuccessDTO(uid=data.uid)
    else:
        raise HTTPException(status_code=404, detail="Input not found")

