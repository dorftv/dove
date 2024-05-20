from fastapi import APIRouter, Request, HTTPException
from api.websockets import manager
from pipeline_handler import PipelineHandler
from pipelines.description import Description
from pipelines.base import GSTBase
from api.output_models import OutputDTO, SuccessDTO, OutputDeleteDTO

from api.helper import get_routers
from api.helper import get_model_fields

router = APIRouter()

# Discover and include Routes for Outputs
for router_module, module_name in get_routers('api.outputs'):
    router.include_router(router_module, prefix="/outputs", tags=['Outputs'])

# List avalable Output Types
@router.get("/outputs/types", tags=['Outputs', 'Config'])
async def get_fields():
    return get_model_fields('api.outputs',{'OutputDTO'})

# List all Outputs
@router.get("/outputs", tags=['Outputs'])
async def all(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    outputs: list[Output] = handler._pipelines["outputs"] if handler._pipelines is not None else []
    descriptions: list[Description] = []

    for pipeline in outputs:
        descriptions.append(pipeline.describe())
    return descriptions

# Delete an Output
@router.delete("/outputs", tags=['Outputs'], response_model=SuccessDTO)
async def delete(request: Request, data: OutputDeleteDTO):
    handler: PipelineHandler = request.app.state._state["pipeline_handler"]
    handler.delete_pipeline("outputs", data.uid)
    await manager.broadcast("DELETE", data)

    return SuccessDTO(uid=data.uid)

