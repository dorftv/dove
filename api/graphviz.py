from fastapi import APIRouter, Response, Request
import graphviz
from gi.repository import Gst, GLib



router = APIRouter()
router = APIRouter(prefix="/api")

@router.get("/debug")
async def debug_pipelines(request: Request):
    handler: GSTBase = request.app.state._state["pipeline_handler"]
    pipeline_types = ["inputs", "outputs", "mixers"]

    graph_images = []

    for pipeline_type in pipeline_types:
        pipelines = handler.get_pipelines(pipeline_type)
        if not pipelines:
            continue

        for pipeline in pipelines:
            inner_pipeline = pipeline.inner_pipelines[0]
            dot_graph = Gst.debug_bin_to_dot_data(inner_pipeline, Gst.DebugGraphDetails.ALL)

            graph = graphviz.Source(dot_graph)
            svg_image = graph.pipe(format='svg').decode('utf-8')
            graph_images.append(svg_image)

    html_content = """
    <html>
    <head>
        <title>Pipeline Graphs</title>
    </head>
    <body>
        <h1>Pipeline Graphs</h1>
        {}
    </body>
    </html>
    """.format("\n".join([f"<div>{image}</div>" for image in graph_images]))

    return Response(content=html_content, media_type="text/html")

