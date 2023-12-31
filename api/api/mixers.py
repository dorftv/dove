from typing import Annotated
from uuid import UUID
from typing import Union
from fastapi import APIRouter, Request, HTTPException, Depends
from pydantic import ValidationError
from api.mixers_dtos import mixerDTO, SuccessDTO, MixerDeleteDTO, mixerMixerDTO, outputMixerDTO
from api.websockets import manager
from caps import Caps
from pipeline_handler import PipelineHandler
from pipelines.description import Description
from pipelines.base import GSTBase
from pipelines.mixers.output_mixer import outputMixer
from pipelines.mixers.mixer_mixer import mixerMixer

# @TODO find a better place
from pipelines.outputs.preview_hls_output import previewHlsOutput
from api.outputs_dtos import previewHlsOutputDTO, OutputDTO, OutputDeleteDTO

from uuid import UUID, uuid4

router = APIRouter(prefix="/api")

unionMixerDTO = Union[mixerMixerDTO, outputMixerDTO]
async def handle_mixer(request: Request, data: unionMixerDTO):
    handler: GSTBase = request.app.state._state["pipeline_handler"]

    # Handle based on the type of data
    if isinstance(data, mixerMixerDTO):
        mixer = mixerMixer(data=data)
    elif isinstance(data, outputMixerDTO):
        mixer = outputMixer(data=data)
    else:
        raise HTTPException(status_code=400, detail="Invalid mixer type")

    handler.add_pipeline(mixer)
    # @TODO find a better place 
    # @TODO need a way to delete       
    output = previewHlsOutput(data=previewHlsOutputDTO(src=data.uid))
    handler.add_pipeline(output)    
    await manager.broadcast("CREATE", data)
    return data


async def getMixerDTO(request: Request) -> unionMixerDTO:
    print("req", await request.body())
    json_data = await request.json()
    mixer_type = json_data.get("type")
    try:
        if mixer_type == "mixer":
            return mixerMixerDTO(**json_data)
        elif mixer_type == "preview" or mixer_type == "program":
            return outputMixerDTO(**json_data)
        else:
            raise HTTPException(status_code=400, detail=f"Invalid mixer type: {mixer_type}")
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())

@router.get("/mixers")
async def all(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    mixers: list[Mixer] = handler._pipelines["mixers"]
    descriptions: list[Description] = []

    for pipeline in mixers:
        descriptions.append(pipeline.describe())

    return descriptions

# @TODO handle updates
unionMixerDTO = unionMixerDTO
@router.put("/mixers")
async def create(request: Request, data: unionMixerDTO = Depends(getMixerDTO)):
    return await handle_mixer(request, data)


@router.delete("/mixers", response_model=SuccessDTO)
async def delete(request: Request, data: MixerDeleteDTO):
    handler: PipelineHandler = request.app.state._state["pipeline_handler"]
    handler.delete_pipeline("mixers", data.uid)
    preview = handler.get_preview_pipeline(data.uid)
    await manager.broadcast("DELETE", data)
    await manager.broadcast("DELETE", data=(OutputDeleteDTO(uid=preview.data.uid )))
    return SuccessDTO(code=200, details="OK")

