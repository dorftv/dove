from fastapi import APIRouter, Request, HTTPException
from pipeline_handler import PipelineHandler

from pipelines.base import GSTBase
from api.output_models import OutputDTO, SuccessDTO, OutputDeleteDTO
from api.auth import require_role, require_read

from api.helper import get_routers
from api.helper import get_model_fields

router = APIRouter()

# Discover and include Routes for Outputs (PUT creates output → dove-outputs)
for router_module, module_name in get_routers('api.outputs'):
    router.include_router(router_module, prefix="/outputs", tags=['Outputs'],
                          dependencies=[require_role("outputs")])

# List avalable Output Types
@router.get("/outputs/types", tags=['Outputs', 'Config'], dependencies=[require_read()])
async def get_output_models():
    return get_model_fields('api.outputs',{'OutputDTO'})

# List all Outputs
@router.get("/outputs", tags=['Outputs'], dependencies=[require_read()])
async def get_all_outputs(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    outputs: list[Output] = handler._pipelines["outputs"] if handler._pipelines is not None else []
    descriptions = []

    for pipeline in outputs:
        descriptions.append(pipeline.describe())
    return descriptions

# Delete an Output
@router.delete("/outputs", tags=['Outputs'], response_model=SuccessDTO, dependencies=[require_role("outputs")])
async def delete_output(request: Request, data: OutputDeleteDTO):
    handler: PipelineHandler = request.app.state._state["pipeline_handler"]
    pipeline = handler.get_pipeline("outputs", data.uid)
    if pipeline is not None and getattr(pipeline.data, 'locked', False):
        raise HTTPException(status_code=403, detail="Output is locked")
    handler.delete_pipeline("outputs", data.uid)
    return SuccessDTO(uid=data.uid)

