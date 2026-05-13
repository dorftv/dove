from fastapi import APIRouter, Response, Request
from fastapi.responses import PlainTextResponse
from gi.repository import Gst
import html as html_mod
from dove.api.auth import require_role

router = APIRouter(prefix="/api/debug", dependencies=[require_role("admin")])

# Exclude NON_DEFAULT_PARAMS and FULL_PARAMS — querying properties on
# orphaned webrtcbin elements crashes (freed ICE agent).
_SAFE_GRAPH_DETAILS = (
    Gst.DebugGraphDetails.MEDIA_TYPE
    | Gst.DebugGraphDetails.CAPS_DETAILS
    | Gst.DebugGraphDetails.STATES
)


@router.get("/graphviz")
async def debug_pipelines(request: Request):
    handler = request.app.state.pipeline_handler

    sections = []

    # Component tables
    for pipeline_type in ["inputs", "mixers", "outputs"]:
        pipelines = handler.get_pipelines(pipeline_type)
        if not pipelines:
            continue

        rows = []
        for p in pipelines:
            d = p.data
            uid = str(d.uid)[:8]
            name = html_mod.escape(str(d.name))
            ptype = html_mod.escape(str(getattr(d, 'type', '-')))
            state = html_mod.escape(str(getattr(d, 'state', '-')))
            extra = ""
            if pipeline_type == "outputs":
                src = str(getattr(d, 'src', '-'))[:8]
                extra = f"<td>{src}</td>"
            if pipeline_type == "mixers":
                sources = getattr(d, 'sources', [])
                src_list = ", ".join(str(s.src)[:8] for s in sources if s.src and str(s.src) != "None")
                extra = f"<td>{html_mod.escape(src_list or '-')}</td>"
            rows.append(f"<tr><td>{uid}</td><td>{name}</td><td>{ptype}</td><td>{state}</td>{extra}</tr>")

        extra_header = ""
        if pipeline_type == "outputs":
            extra_header = "<th>src</th>"
        if pipeline_type == "mixers":
            extra_header = "<th>sources</th>"

        table = f"""
        <h2>{pipeline_type.title()}</h2>
        <table>
            <tr><th>uid</th><th>name</th><th>type</th><th>state</th>{extra_header}</tr>
            {"".join(rows)}
        </table>"""
        sections.append(table)

    # Connection map
    connections = []
    mixers = handler.get_pipelines("mixers") or []
    outputs = handler.get_pipelines("outputs") or []
    for m in mixers:
        sources = getattr(m.data, 'sources', [])
        for s in sources:
            if s.src and str(s.src) != "None":
                connections.append(f"<li>{str(s.src)[:8]} &rarr; {html_mod.escape(m.data.name)} (slot {s.index})</li>")
    for o in outputs:
        src = getattr(o.data, 'src', None)
        if src:
            connections.append(f"<li>{str(src)[:8]} &rarr; {html_mod.escape(o.data.name)}</li>")

    if connections:
        sections.append(f"<h2>Connections</h2><ul>{''.join(connections)}</ul>")

    # GStreamer pipeline graph
    svg_section = ""
    pipeline = getattr(handler.core_pipeline, 'pipeline', None)
    if pipeline:
        dot_data = Gst.debug_bin_to_dot_data(pipeline, _SAFE_GRAPH_DETAILS)
        try:
            import graphviz
            graph = graphviz.Source(dot_data)
            svg = graph.pipe(format='svg').decode('utf-8')
            svg_section = f"""
            <h2>Pipeline Graph</h2>
            <div style="overflow:auto;border:1px solid #ccc;padding:10px;max-height:80vh;">
                {svg}
            </div>"""
        except Exception as e:
            svg_section = f"<h2>Pipeline Graph</h2><p>SVG rendering failed: {html_mod.escape(str(e))}</p><p><a href='/api/debug/graphviz/dot'>Raw DOT</a></p>"
    else:
        svg_section = "<h2>Pipeline Graph</h2><p>No pipeline available</p>"

    sections.append(svg_section)

    page = f"""<!DOCTYPE html>
<html>
<head>
    <title>DOVE Debug - Graphviz</title>
    <style>
        body {{ font-family: sans-serif; margin: 20px; background: #1a1a1a; color: #e0e0e0; }}
        h1 {{ color: #fff; }}
        h2 {{ color: #ccc; border-bottom: 1px solid #444; padding-bottom: 5px; }}
        table {{ border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ border: 1px solid #444; padding: 6px 12px; text-align: left; }}
        th {{ background: #333; }}
        tr:nth-child(even) {{ background: #222; }}
        a {{ color: #6cf; }}
        ul {{ list-style: none; padding: 0; }}
        li {{ padding: 2px 0; }}
        li::before {{ content: "→ "; color: #888; }}
        nav a {{ margin-right: 12px; }}
    </style>
</head>
<body>
    <h1>DOVE Debug - Graphviz</h1>
    <nav>
        <a href="/api/debug/graphviz/dot">Raw DOT</a>
        <a href="/api/debug/docs">Swagger UI</a>
    </nav>
    {"".join(sections)}
</body>
</html>"""

    return Response(content=page, media_type="text/html")


@router.get("/graphviz/dot")
async def debug_dot(request: Request):
    handler = request.app.state.pipeline_handler
    pipeline = getattr(handler.core_pipeline, 'pipeline', None)
    if not pipeline:
        return PlainTextResponse("No pipeline available", status_code=404)

    dot_data = Gst.debug_bin_to_dot_data(pipeline, _SAFE_GRAPH_DETAILS)
    return PlainTextResponse(dot_data, media_type="text/vnd.graphviz")


