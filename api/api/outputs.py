# from fastapi import APIRouter, Request
#
# from models.input import OutputDTO, InputCreateDTO, Description
#
# router = APIRouter(prefix="/api")
#
# @router.get("/outputs", response_model=list[InputCreateDTO])
# async def all_outputs(request: Request):
#     handler = request.app.state._state["pipeline_handler"]
#     outputs = handler.pipelines["outputs"]
#
#     descriptions: list[Description] = []
#     for pipeline in outputs:
#         descriptions.append(pipeline.describe())
#
#     return descriptions
#
# @router.put("outputs")
# async def create_output(request: Request):
#     pass