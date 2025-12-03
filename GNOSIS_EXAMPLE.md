# GNOSIS Earth Integration - Quick Start Example

## Example: Query SRTM Data for San Francisco Bay Area

This example shows how to use the GNOSIS DGGS Agent from QGIS Python console.

### Step 1: Import Required Modules

```python
from qgis.core import QgsRectangle, QgsProject
import sys
import os

# Add plugin path
plugin_path = os.path.expanduser('~/Library/Application Support/QGIS/QGIS3/profiles/default/python/plugins/copexporter')
sys.path.append(plugin_path)

from gnosis_dggs_agent import GnosisDGGSAgent
```

### Step 2: Initialize Agent

```python
# Create agent instance
agent = GnosisDGGSAgent()
```

### Step 3: Define Area of Interest

```python
# San Francisco Bay Area extent (WGS84)
extent = QgsRectangle(
    -122.5,  # xmin (West)
    37.7,    # ymin (South)
    -122.3,  # xmax (East)
    37.9     # ymax (North)
)

print(f"Query extent: {extent.toString()}")
```

### Step 4: Query GNOSIS Earth

```python
# Get coverage summary
summary = agent.get_coverage_summary(extent, dggs_crs="rHEALPix-R12")

if summary['success']:
    print(f"\n✓ Query successful!")
    print(f"DGGS Zones: {summary['zone_count']}")
    print(f"Features: {summary['feature_count']}")
    
    if summary.get('zones'):
        print(f"Zone IDs: {', '.join(summary['zones'][:5])}")
    
    if 'elevation_stats' in summary:
        elev = summary['elevation_stats']
        print(f"Elevation Range: {elev['min']}m to {elev['max']}m")
else:
    print(f"✗ Query failed: {summary['error']}")
```

### Step 5: Get Detailed Zone Information

```python
# Get list of all DGGS zones
zones = agent.get_dggs_zones_for_extent(extent, "rHEALPix-R12")

print(f"\nFound {len(zones)} DGGS zones:")
for zone in zones:
    print(f"  - {zone}")
```

### Step 6: Fetch and Save Data

```python
# Download data as GeoJSON
output_path = os.path.expanduser('~/Desktop/gnosis_sf_bay.geojson')

success = agent.fetch_and_save_geojson(
    extent, 
    output_path,
    dggs_crs="rHEALPix-R12"
)

if success:
    print(f"\n✓ Data saved to: {output_path}")
    
    # Add to QGIS map
    from qgis.core import QgsVectorLayer
    layer = QgsVectorLayer(output_path, "GNOSIS SRTM Bay Area", "ogr")
    
    if layer.isValid():
        QgsProject.instance().addMapLayer(layer)
        print("✓ Layer added to map")
    else:
        print("✗ Could not add layer")
else:
    print(f"✗ Failed to save: {agent.last_error}")
```

## Expected Output

```
Query extent: -122.5000000000000000,37.7000000000000028 : -122.3000000000000043,37.9000000000000057

✓ Query successful!
DGGS Zones: 12
Features: 456
Zone IDs: R05_08, R05_09, R06_08, R06_09, R06_10
Elevation Range: 0m to 927m

Found 12 DGGS zones:
  - R05_08
  - R05_09
  - R06_08
  - R06_09
  - R06_10
  - R06_11
  - R07_08
  - R07_09
  - R07_10
  - R07_11
  - R08_09
  - R08_10

✓ Data saved to: /Users/username/Desktop/gnosis_sf_bay.geojson
✓ Layer added to map
```

## Alternative: Use from Current Map Extent

```python
# Get extent from current map canvas
from qgis.utils import iface

map_extent = iface.mapCanvas().extent()
map_crs = iface.mapCanvas().mapSettings().destinationCrs()

# Transform to WGS84 if needed
extent_wgs84 = agent.transform_extent_to_wgs84(map_extent, map_crs)

# Query with map extent
summary = agent.get_coverage_summary(extent_wgs84, "rHEALPix-R12")
```

## Using Different DGGS CRS

```python
# Try different DGGS coordinate systems
dggs_options = ["rHEALPix-R12", "H3", "ISEA3H"]

for dggs_crs in dggs_options:
    print(f"\n=== Testing {dggs_crs} ===")
    summary = agent.get_coverage_summary(extent, dggs_crs)
    
    if summary['success']:
        print(f"Zones: {summary['zone_count']}, Features: {summary['feature_count']}")
```

## Error Handling Example

```python
import urllib.error

try:
    # Query with invalid extent (will fail)
    bad_extent = QgsRectangle(0, 0, 0, 0)
    result = agent.query_dggs_data(bad_extent, "rHEALPix-R12")
    
    if not result:
        print(f"Error: {agent.last_error}")
        
except Exception as e:
    print(f"Exception: {str(e)}")
```

## Integration with COP STAC Export

```python
# After querying GNOSIS, use zone IDs in COP export
zones = agent.get_dggs_zones_for_extent(extent, "rHEALPix-R12")

if zones:
    primary_zone = zones[0]
    print(f"Using DGGS Zone ID: {primary_zone}")
    
    # This zone ID can be used in COP metadata:
    # cop:dggs_zone_id = primary_zone
    # cop:dggs_crs = "rHEALPix-R12"
```

## Performance Tips

1. **Cache Results**: Store query results to avoid repeated API calls
   ```python
   cached_data = agent.last_response
   ```

2. **Limit Extent Size**: Smaller extents = faster queries
   ```python
   # Good: ~0.2 x 0.2 degrees
   small_extent = QgsRectangle(-122.5, 37.7, -122.3, 37.9)
   
   # Avoid: Very large extents
   # huge_extent = QgsRectangle(-180, -90, 180, 90)
   ```

3. **Use Zone IDs**: Query specific zones when known
   ```python
   result = agent.query_dggs_data(extent, "rHEALPix-R12", zone_id="R05_08")
   ```

## Troubleshooting

### "QGIS not available" Error
Run from QGIS Python console, not standalone Python.

### Network Timeout
```python
# Check network connectivity
import urllib.request
try:
    urllib.request.urlopen('https://maps.gnosis.earth', timeout=5)
    print("Network OK")
except:
    print("Network issue")
```

### No Features Returned
- Check extent is valid (xmin < xmax, ymin < ymax)
- Verify extent is in WGS84 (EPSG:4326)
- Try a different DGGS CRS
- Check GNOSIS Earth API status

## See Also

- [GNOSIS_DGGS_AGENT.md](GNOSIS_DGGS_AGENT.md) - Full API documentation
- [GNOSIS_IMPLEMENTATION.md](GNOSIS_IMPLEMENTATION.md) - Implementation details
- [README.md](README.md) - Plugin overview
