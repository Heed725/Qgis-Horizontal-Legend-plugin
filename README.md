# QGIS Horizontal Legend Plugin

A lightweight QGIS plugin that makes it easy to turn a standard **Print Layout legend** into a compact horizontal legend.

## Features

- Adds a **Horizontal Legend** icon to the main QGIS toolbar.
- Adds the same icon/action inside newly opened **Print Layout** designer windows.
- Works on the currently selected native QGIS Legend item.
- Prompts for the number of horizontal columns.
- Enables split-layer legend layout and compact spacing.
- Resizes and refreshes the legend after applying the change.
- Keeps the result fully editable using normal QGIS **Item Properties**.
- Includes GitHub Actions packaging for an installable plugin ZIP.

## Supported QGIS versions

- Minimum: QGIS 3.22
- Intended for QGIS 3.x releases through 3.99

## Installation from ZIP

1. Download `qgis-horizontal-legend.zip` from the latest GitHub Actions artifact or a tagged GitHub Release.
2. Open QGIS.
3. Go to **Plugins > Manage and Install Plugins**.
4. Open **Install from ZIP**.
5. Select the downloaded ZIP and install it.
6. Ensure **Horizontal Legend** is enabled in the Installed plugins list.

## Usage

1. Open a project in QGIS.
2. Open or create a **Print Layout**.
3. Add a normal QGIS **Legend** item to the layout.
4. Select that Legend item.
5. Click the **Horizontal Legend** icon in the Print Layout window.
6. Enter the number of columns you want.
7. The plugin arranges the legend horizontally and refreshes the layout.
8. Use **Item Properties** for any final typography, symbol-size, spacing, title, or frame adjustments.

## How it works

The plugin uses QGIS' native `QgsLayoutItemLegend` API. It changes the legend's column count, permits layer entries to split between columns, applies compact column/box spacing, and asks QGIS to resize the legend to its new contents. Because the result remains a standard layout legend, it continues to respond to layer/style changes as normal.

## Print Layout integration

The plugin listens for QGIS Print Layout designer windows. When one opens, it adds a **Horizontal Legend** QAction using the bundled SVG icon to a layout toolbar and also provides a dedicated layout menu entry. A main-window toolbar action is included as a fallback.

## Automated packaging

`.github/workflows/package-plugin.yml` runs on pushes, pull requests, manual dispatches, and version tags.

It:

- validates required plugin files;
- syntax-compiles the Python source;
- creates `qgis-horizontal-legend.zip` with the required top-level `qgis_horizontal_legend/` plugin directory;
- uploads the ZIP as a GitHub Actions artifact;
- automatically creates a GitHub Release and attaches the ZIP when a tag such as `v1.0.0` is pushed.

## Plugin structure

```text
qgis_horizontal_legend/
├── __init__.py
├── plugin.py
├── metadata.txt
└── icon.svg
```

## Development

For local development, copy or clone the `qgis_horizontal_legend` folder into your QGIS profile's `python/plugins` directory, restart QGIS, and enable the plugin from the Plugin Manager.

## License

MIT License.
