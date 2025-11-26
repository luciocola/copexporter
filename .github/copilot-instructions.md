# COP STAC Exporter - AI Coding Instructions

## Project Overview

This is a **QGIS 3.x plugin** that exports geospatial layers to STAC (SpatioTemporal Asset Catalog) v1.0.0 format with the COP (Common Operating Picture) extension v1.0.0. Target users are emergency response personnel who need to share geospatial data with security classifications.

## Architecture

### Three-Layer Structure
1. **Plugin Shell** (`copexporter.py`, `__init__.py`): QGIS plugin lifecycle management using standard QGIS plugin architecture
2. **UI Layer** (`cop_stac_dialog.py` + `ui/cop_stac_dialog.ui`): PyQt5 dialog for user interaction, loaded via `uic.loadUiType()`
3. **Core Export Logic** (`stac_cop_exporter.py`): Pure Python STAC generation, isolated from QGIS UI concerns

**Note:** There are duplicate dialog files (`copexporter_dialog.py` is legacy; `cop_stac_dialog.py` is active).

### Key Data Flow
```
User Selection → COPSTACDialog → STACCOPExporter → STAC Items/Collection
                     ↓                    ↓
              cop_metadata dict    GeoJSON assets + JSON metadata
```

## Critical QGIS Patterns

### Layer Handling
- Access project layers via `QgsProject.instance().mapLayers().values()`
- Store layer references using `layer.id()` in `Qt.UserRole`, NOT layer objects (they can become invalid)
- Check layer type with `isinstance(layer, QgsVectorLayer)` or `isinstance(layer, QgsRasterLayer)`

### Vector Export (GeoJSON)
Uses QGIS 3.x API:
```python
QgsVectorFileWriter.writeAsVectorFormatV3(
    layer, output_file,
    QgsProject.instance().transformContext(),
    options
)
```
**Not** the older `writeAsVectorFormat()` method.

### CRS Transformations
Always transform extents to EPSG:4326 for STAC compliance:
```python
transform = QgsCoordinateTransform(
    layer.crs(),
    QgsCoordinateReferenceSystem('EPSG:4326'),
    QgsProject.instance()
)
extent = transform.transformBoundingBox(extent)
```

## STAC Specification Requirements

### COP Extension Fields (in item properties)
- `cop:mission` - Mission/operation identifier
- `cop:classification` - Security level (public release, internal, confidential, restricted, classified)
- `cop:releasability` - Data sharing specification
- `cop:dggs_crs` - DGGS Coordinate Reference System (default: "rHEALPix-R12")
- `cop:dggs_zone_id` - Optional DGGS zone identifier
- `cop:service_provider` - Optional data/service provider
- `cop:asset_type` - In assets, not properties ("feature" for vector, "imagery" for raster)

### Extension Declaration
Every STAC Item/Collection must include:
```json
"stac_extensions": [
  "https://stac-extensions.github.io/cop/v1.0.0/schema.json"
]
```

### ID Sanitization
Layer names → STAC IDs via `sanitize_id()`: alphanumeric + `-_` only, lowercase, must start with alphanumeric.

## File Structure Conventions

### Output Directory Layout
```
output_dir/
└── stac_cop_export/           # Created by STACCOPExporter
    ├── collection.json         # STAC Collection
    ├── {layer_id}.json         # STAC Items
    └── assets/
        └── {layer_id}.geojson  # Exported layer data
```

### Relative Paths in STAC
Asset hrefs are **relative to the STAC item JSON file**:
```python
"href": os.path.relpath(asset_path, self.stac_dir)
```

## Development Workflows

### Testing During Development
No automated tests exist. Manual testing requires:
1. Install plugin: `pb_tool deploy` (uses `pb_tool.cfg` config)
2. Restart QGIS to reload Python modules
3. Enable plugin in QGIS: Plugins → Manage and Install Plugins → Installed
4. Test via toolbar icon or Plugins menu

### Plugin Installation Paths
- macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
- Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
- Windows: `%APPDATA%/QGIS/QGIS3/profiles/default/python/plugins/`

### UI Modifications
Qt Designer UI files (`ui/cop_stac_dialog.ui`) are loaded at runtime via `uic.loadUiType()` - no compilation step needed. Widget names in `.ui` must match Python code references (e.g., `self.btnExport`).

### Resources
`resources.qrc` compiled to `resources.py` for icons. Icon paths use Qt resource syntax: `':/plugins/copexporter/icon.png'`

## Common Pitfalls

1. **Collection Creation**: Currently `create_collection()` is defined but never called. Export workflow doesn't generate `collection.json`.

2. **Raster Export**: For `QgsRasterLayer`, the code references `layer.source()` (original file path) instead of copying/processing the raster. This breaks portability.

3. **Datetime Format**: Uses `datetime.now(timezone.utc).isoformat()` - STAC compliant, but items always have current timestamp, not layer-specific temporal metadata.

4. **Error Handling**: Export continues even if individual layers fail (see `cop_stac_dialog.py:140-145`). Only shows warnings, doesn't halt process.

5. **Metadata Validation**: No validation that required COP fields (mission, classification) are populated before export.

## Extension Points

When adding features:
- **New COP fields**: Add to `cop_metadata` dict in `cop_stac_dialog.py:121-128`, then to STAC properties in `stac_cop_exporter.py:189-205`
- **New layer types**: Extend `export_layer_data()` with additional `isinstance()` checks
- **Custom STAC extensions**: Add to `stac_extensions` array in both `create_stac_item()` and `create_collection()`
