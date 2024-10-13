from fastapi import APIRouter, Request
from pydantic import Field
from api.output_models import OutputDTO, SuccessDTO
from typing import Optional,  Literal, Union
from api.encoder.audio_encoder import mp3EncoderDTO

from api.websockets import manager



router = APIRouter()

class Shout2sendOutputDTO(OutputDTO):
    type: str = Field(
        label="Shout2Send",
        default="shout2send",
        description="Send audio to Icecast Server.",
    )
    mount: str = Field(
        label="Mountpoint",
        description="Mountpoint to connect to the server",
        help="currently only mp3 is supported.",
        placeholder="/stream.mp3"
    )
    ip: str = Field(
        label="Ip",
        help="Ip to connect to the server.",
        placeholder="192.168.1.100"
    )
    port: int = Field(
        label="Port",
        help="Port to connect to the server.",
        placeholder="8000"
    )
    username: str = Field(
        label="User",
        help="User to connect to the server.",
        placeholder="user"
    )
    password: str = Field(
        label="Password",
        help="Password to connect to the server.",
        placeholder="password"
    )
    audio_encoder: Union[mp3EncoderDTO] = Field(
        default_factory=lambda: mp3EncoderDTO(
            name="mp3",
            options="target=bitrate bitrate=192"
        )
    )

from pipelines.outputs.shout2send import Shout2sendOutput

@router.put("/shout2send", response_model=SuccessDTO)
async def create_srtsink_output(request: Request, data: Shout2sendOutputDTO):
    handler = request.app.state._state["pipeline_handler"]
    output = handler.get_pipeline("outputs", data.uid)

    if output:
        output.data = data
    else:
        output = DecklinkOutput(data=data)
        handler.add_pipeline(output)

    await manager.broadcast("CREATE", data)

    return data