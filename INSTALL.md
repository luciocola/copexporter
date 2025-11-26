# Installation and Setup Guide

## Quick Start

### 1. Install in QGIS

Copy the entire `cop_stac_exporter` folder to your QGIS plugins directory:

**macOS:**
```bash
cp -r cop_stac_exporter ~/Library/Application\ Support/QGIS/QGIS3/profiles/default/python/plugins/
```

**Linux:**
```bash
cp -r cop_stac_exporter ~/.local/share/QGIS/QGIS3/profiles/default/python/plugins/
```

**Windows:**
```cmd
xcopy cop_stac_exporter "C:\Users\%USERNAME%\AppData\Roaming\QGIS\QGIS3\profiles\default\python\plugins\cop_stac_exporter" /E /I
```

### 2. Enable the Plugin

1. Open QGIS
2. Go to `Plugins` → `Manage and Install Plugins`
3. Go to the `Installed` tab
4. Find "COP STAC Exporter" and check the box to enable it

### 3. Use the Plugin

1. Click the COP STAC Exporter icon in the toolbar
2. Select layers to export
3. Fill in COP metadata fields
4. Choose output directory
5. Click Export!

## Example Workflow

### Emergency Response Scenario

1. **Load your operational layers** (e.g., flood extent, resource locations, affected areas)

2. **Open COP STAC Exporter** from the toolbar

3. **Configure COP metadata:**
   - Mission: "Flood Response 2025-11"
   - Classification: "internal"
   - Releasability: "Emergency Response Team"
   - DGGS CRS: "rHEALPix-R12"
   - DGGS Zone ID: "R312603625535"

4. **Select output directory** and enable ZIP creation

5. **Click Export** - Your STAC catalog is ready to share!

## Output Files

After export, you'll have:

```
your_output_folder/
├── stac_cop_export/
│   ├── collection.json          # STAC Collection metadata
│   ├── flood_extent.json        # STAC Item for flood layer
│   ├── resources.json           # STAC Item for resources layer
│   └── assets/
│       ├── flood_extent.geojson
│       └── resources.geojson
└── stac_cop_export_20251126_143022.zip
```

## Troubleshooting

### Plugin doesn't appear in QGIS
- Make sure you copied to the correct plugins directory
- Restart QGIS completely
- Check that the folder name is exactly `cop_stac_exporter`

### Export fails
- Ensure output directory is writable
- Check that layers are valid (not broken)
- Verify layer CRS is defined

### ZIP creation fails
- Ensure enough disk space
- Check folder permissions

## Advanced Usage

### Custom DGGS Integration

The plugin supports any DGGS system. Simply specify:
- DGGS CRS (e.g., "rHEALPix-R12", "H3-res9", "S2-level15")
- DGGS Zone ID (the specific cell identifier)

### Batch Export

To export multiple projects:
1. Open first project
2. Run export
3. Open next project
4. Repeat

All exports can use the same output directory - each will create a timestamped ZIP.

## Support

Issues? Questions? Visit: https://github.com/luciocola/cop-stac-exporter/issues
