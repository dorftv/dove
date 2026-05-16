# Test Source

The test source input generates synthetic video and audio. No external media or network connection is required.

## Use Cases

- Verify the pipeline is running before connecting real sources
- Test scene compositions and output configurations
- Fill empty slots with a visible signal during setup

## Video Patterns

The `pattern` field selects the video test pattern:

| Value | Pattern |
|-------|---------|
| `smpte` | SMPTE color bars (default) |
| `snow` | Random noise |
| `black` | Solid black |
| `white` | Solid white |
| `red` | Solid red |
| `green` | Solid green |
| `blue` | Solid blue |
| `checkers-1` | 1-pixel checkerboard |
| `ball` | Moving ball |
| `zone-plate` | Zone plate (frequency sweep) |

## Audio

The audio test source generates a sine wave tone at 440 Hz by default. Volume can be adjusted via the standard input volume control.

## Fields

| Field | Description |
|-------|-------------|
| Pattern | Video test pattern (see table above) |
