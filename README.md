# COP STAC Exporter - QGIS Plugin

Export QGIS map layers to STAC (SpatioTemporal Asset Catalog) format with COP (Common Operating Picture) extension support.

## Features

- **Layer Selection**: Choose specific layers from the current QGIS project
- **COP Metadata**: Configure Common Operating Picture fields including:
  - Mission/operation identifier
  - Security classification (public release, internal, confidential, restricted, classified)
  - Releasability specification
  - DGGS (Discrete Global Grid System) support with zone IDs and CRS
  - Service provider information
- **Multiple Export Formats**: 
  - Vector layers exported as GeoJSON
  - Raster layers referenced in STAC
- **ZIP Archive**: Optional compression of all exported files
- **STAC Compliance**: Fully compliant with STAC v1.0.0 specification
- **COP Extension**: Implements the COP STAC extension v1.0.0

## Installation

### From QGIS Plugin Manager (when published)
1. Open QGIS
2. Go to `Plugins > Manage and Install Plugins`
3. Search for "COP STAC Exporter"
4. Click Install

### Manual Installation
1. Download or clone this repository
2. Copy the `cop_stac_exporter` folder to your QGIS plugins directory:
   - Windows: `C:\Users\<YourUser>\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\`
   - macOS: `~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/`
   - Linux: `~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/`
3. Restart QGIS
4. Enable the plugin in `Plugins > Manage and Install Plugins > Installed`

## Usage

1. **Open the Plugin**
   - Click the COP STAC Exporter icon in the toolbar
   - Or go to `Plugins > COP STAC Exporter > Export Layers to STAC COP`

2. **Select Layers**
   - All layers from the current project are listed
   - Use checkboxes to select layers to export
   - Use "Select All" or "Deselect All" for bulk operations

3. **Configure COP Metadata**
   - **Mission**: Enter mission or operation identifier
   - **Classification**: Select security classification level
   - **Releasability**: Specify who can access the data (e.g., "1:N")
   - **DGGS CRS**: Enter DGGS Coordinate Reference System (e.g., "rHEALPix-R12")
   - **DGGS Zone ID**: Optionally specify a DGGS zone identifier
   - **Service Provider**: Optionally specify data/service provider

4. **Select Output**
   - Click "Browse" to select output directory
   - Check "Create ZIP archive" if you want a compressed file

5. **Export**
   - Click "Export" to generate STAC files
   - Files will be created in a `stac_cop_export` subdirectory
   - If ZIP is selected, a timestamped archive will be created

## Output Structure

```
output_directory/
├── stac_cop_export/
│   ├── collection.json          # STAC Collection
│   ├── layer1.json              # STAC Item for layer 1
│   ├── layer2.json              # STAC Item for layer 2
│   └── assets/
│       ├── layer1.geojson       # Exported layer data
│       └── layer2.geojson
└── stac_cop_export_20251126_120000.zip  # Optional ZIP archive
```

## STAC COP Extension Fields

The plugin supports the following COP extension fields:

- `cop:mission` - Mission or operation identifier
- `cop:classification` - Security classification level
- `cop:releasability` - Data releasability specification
- `cop:dggs_zone_id` - DGGS zone identifier
- `cop:dggs_crs` - DGGS Coordinate Reference System
- `cop:service_provider` - Service or data provider
- `cop:asset_type` - Type of asset (feature, imagery, etc.)

## Requirements

- QGIS 3.0 or higher
- Python 3.6+

## License

Apache License 2.0 - See LICENSE file for details

## Author

Lucio Colaiacomo - [Secure Dimensions](https://secure-dimensions.de)

## Links

- [STAC Specification](https://github.com/radiantearth/stac-spec)
- [COP Extension](https://github.com/luciocola/cop)
- [DGGS Information](https://www.ogc.org/standards/dggs)

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/luciocola/cop-stac-exporter/issues).

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
