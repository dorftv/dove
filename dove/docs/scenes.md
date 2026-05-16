# Scenes

A **scene** is a layout that combines one or more inputs into a single video and audio mix.

## Slots

Each scene has a fixed number of **input slots**. Assign an input to a slot to include it in the mix. Slots can be left empty — empty slots contribute nothing to the output.

### Video Slot Properties

| Property | Description |
|----------|-------------|
| `xpos` | Horizontal position in pixels (from left) |
| `ypos` | Vertical position in pixels (from top) |
| `width` | Width in pixels (0 = use source width) |
| `height` | Height in pixels (0 = use source height) |
| `alpha` | Opacity, 0.0 (transparent) to 1.0 (opaque) |
| `zorder` | Stacking order — higher values appear on top |

### Audio Slot Properties

| Property | Description |
|----------|-------------|
| `volume` | Audio level, 0.0 (mute) to 1.0 (full) |

## Switching to Program

To make a scene live:

- Click the scene to select it (shows in preview)
- Press **Cut** or **Enter** to switch it to program

The switch is instantaneous (hard cut). Smooth transitions are not currently supported.

## Scene Configuration

Scenes are defined in `config.toml` under `[scenes]`. The number of slots and the resolution are set at startup and require a restart to change.
