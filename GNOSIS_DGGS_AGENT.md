# GNOSIS Earth DGGS Agent

## Overview

The GNOSIS DGGS Agent integrates with the COP STAC Exporter to query the GNOSIS Earth OGC API for SRTM (Shuttle Radar Topography Mission) ViewFinder Panorama elevation data using Discrete Global Grid System (DGGS) coordinates.

## Features

- **Automatic DGGS Query**: Query SRTM elevation data for your map extent using DGGS coordinates
- **Multiple DGGS CRS Support**: Supports rHEALPix, H3, S2, ISEA3H, and IGEO coordinate systems
- **Coverage Summary**: Get statistics on available data including zone counts and elevation ranges
- **GeoJSON Export**: Download and save GNOSIS data directly as GeoJSON layers
- **Map Integration**: Automatically add retrieved data layers to your QGIS map

## API Endpoint

The agent queries:
```
https://maps.gnosis.earth/ogcapi/collections/SRTM_ViewFinderPanorama/dggs/
```

## Usage

### From COP STAC Exporter Dialog

1. **Select Layers**: Choose one or more layers to define your area of interest
2. **Set DGGS CRS**: Choose your preferred DGGS coordinate system (e.g., rHEALPix-R12)
3. **Click "Query GNOSIS Earth"**: The agent will:
   - Calculate the combined extent of selected layers
   - Transform to WGS84 (EPSG:4326) if needed
   - Query the GNOSIS API with DGGS parameters
   - Display coverage summary

4. **Review Results**: The dialog shows:
   - Number of DGGS zones found
   - Number of elevation features
   - Elevation range (min/max)
   - Geographic extent

5. **Save Data** (Optional): Save the retrieved data as GeoJSON and add to map

### Programmatic Usage

```python
from gnosis_dggs_agent import GnosisDGGSAgent
from qgis.core import QgsRectangle

# Initialize agent
agent = GnosisDGGSAgent()

# Define extent (in EPSG:4326)
extent = QgsRectangle(-122.5, 37.7, -122.3, 37.9)  # San Francisco area

# Query GNOSIS Earth
result = agent.query_dggs_data(extent, dggs_crs="rHEALPix-R12")

if result:
    print(f"Found {len(result['features'])} features")
    
# Get coverage summary
summary = agent.get_coverage_summary(extent, dggs_crs="rHEALPix-R12")
print(f"DGGS Zones: {summary['zone_count']}")
print(f"Features: {summary['feature_count']}")

# Get list of zones
zones = agent.get_dggs_zones_for_extent(extent, "rHEALPix-R12")
print(f"Zone IDs: {zones}")

# Save as GeoJSON
agent.fetch_and_save_geojson(
    extent, 
    "/path/to/output.geojson",
    dggs_crs="rHEALPix-R12"
)
```

## Supported DGGS CRS

| DGGS CRS | Identifier | Resolution Example |
|----------|------------|-------------------|
| rHEALPix | rHEALPix-R12 | 12 levels |
| H3 | H3-R5 | Resolution 5 |
| S2 | S2-L10 | Level 10 |
| ISEA3H | ISEA3H-R12 | Resolution 12 |
| IGEO | IGEO-R10 | Resolution 10 |

## Query Parameters

The agent constructs OGC API queries with:

- **bbox**: Geographic bounding box (xmin,ymin,xmax,ymax in EPSG:4326)
- **dggs-crs**: DGGS coordinate reference system identifier
- **zone-id**: (Optional) Specific DGGS zone to query
- **f**: Response format (json)

Example query:
```
https://maps.gnosis.earth/ogcapi/collections/SRTM_ViewFinderPanorama/dggs/?bbox=-122.5,37.7,-122.3,37.9&dggs-crs=rHEALPix-R12&f=json
```

## Response Format

The API returns GeoJSON FeatureCollection with SRTM elevation data:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "id": "zone_id_here",
      "geometry": { ... },
      "properties": {
        "dggs_zone_id": "R05_08",
        "elevation": 250,
        "resolution": 12,
        ...
      }
    }
  ]
}
```

## Error Handling

The agent handles:
- **HTTP Errors**: Network issues, server errors (500), not found (404)
- **JSON Decode Errors**: Invalid response format
- **Timeout**: 30-second request timeout
- **CRS Transformation**: Automatic conversion to WGS84

All errors are logged to QGIS Message Log under "GNOSIS DGGS Agent" category.

## Methods Reference

### `query_dggs_data(extent, dggs_crs, zone_id=None)`
Query GNOSIS Earth API for raw data.
- **Returns**: dict (GeoJSON) or None on error

### `get_dggs_zones_for_extent(extent, dggs_crs)`
Get list of DGGS zone IDs intersecting the extent.
- **Returns**: list of zone ID strings

### `get_coverage_summary(extent, dggs_crs)`
Get comprehensive coverage summary with statistics.
- **Returns**: dict with success, zone_count, feature_count, elevation_stats, etc.

### `fetch_and_save_geojson(extent, output_path, dggs_crs, zone_id=None)`
Fetch data and save to file.
- **Returns**: bool (True on success)

### `transform_extent_to_wgs84(extent, source_crs)`
Transform extent from any CRS to WGS84.
- **Returns**: QgsRectangle in EPSG:4326

## Integration with COP Extension

The retrieved DGGS data includes:
- `dggs_zone_id`: Zone identifier for COP extension
- `dggs_crs`: Coordinate system for STAC metadata
- Elevation data that can be referenced in STAC items

This data enriches COP STAC exports with validated DGGS zone information from authoritative sources.

## Dependencies

- QGIS Python API (qgis.core)
- Python standard library: json, urllib, os
- No external Python packages required

## License

Part of the COP STAC Exporter plugin.
