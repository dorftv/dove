# Debugging

DOVE provides several built-in debugging tools.

## [Pipeline Debug](/api/debug/graphviz)

HTML page showing the current state of all pipeline components:

- **Component tables** -- lists all inputs, mixers, and outputs with uid, name, type, and state
- **Connection map** -- shows signal flow between inputs, mixers, and outputs
- **Pipeline graph** -- full GStreamer pipeline rendered as SVG

## [Raw DOT Output](/api/debug/graphviz/dot)

Returns the GStreamer pipeline graph as raw DOT text. Use with external tools:

```bash
# View with xdot
curl http://localhost:5000/api/debug/graphviz/dot | xdot -

# Render to PNG
curl http://localhost:5000/api/debug/graphviz/dot | dot -Tpng -o pipeline.png
```

## [Swagger UI](/api/debug/docs)

FastAPI auto-generated Swagger UI for all REST endpoints. Allows interactive testing of the API.

## GStreamer Debug Environment Variables

```bash
# Set debug level (0=none, 5=verbose)
GST_DEBUG=2,urisourcebin:4

# Dump pipeline graphs to directory
GST_DEBUG_DUMP_DOT_DIR=/tmp

# Application log level
LOG_LEVEL=debug
```
