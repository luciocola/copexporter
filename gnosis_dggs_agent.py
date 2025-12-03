"""
GNOSIS Earth DGGS Agent
Retrieves SRTM ViewFinder Panorama data from GNOSIS Earth OGC API for specific areas and DGGS CRS
"""
import json
import urllib.request
import urllib.parse
import urllib.error
from qgis.core import (
    QgsRectangle,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject,
    QgsMessageLog,
    Qgis
)


class GnosisDGGSAgent:
    """Agent for querying GNOSIS Earth OGC API for DGGS-based SRTM data"""
    
    # Default server settings (can be overridden per instance)
    DEFAULT_BASE_URL = "https://maps.gnosis.earth/ogcapi"
    COLLECTION = "SRTM_ViewFinderPanorama"
    
    def __init__(self, base_url=None):
        """
        Initialize the GNOSIS DGGS Agent
        
        Args:
            base_url: Optional custom server URL (defaults to GNOSIS Earth)
        """
        self.BASE_URL = base_url or self.DEFAULT_BASE_URL
        self.last_response = None
        self.last_error = None
    
    def query_dggs_data(self, extent, dggs_crs="rHEALPix", zone_id=None):
        """
        Query GNOSIS Earth API for SRTM data in the specified area and DGGS CRS
        
        Args:
            extent: QgsRectangle in EPSG:4326 (WGS84)
            dggs_crs: DGGS system name (default: rHEALPix)
            zone_id: Optional specific DGGS zone ID to query
            
        Returns:
            dict: Combined GeoJSON FeatureCollection from all zones or None if error
        """
        try:
            # First, get the list of zones that intersect the extent
            if zone_id:
                zones_to_query = [zone_id]
            else:
                zones_to_query = self.get_zones_for_extent(extent, dggs_crs)
                if not zones_to_query:
                    error_msg = "No DGGS zones found for the specified extent"
                    self.last_error = error_msg
                    self.log_message(error_msg, Qgis.Warning)
                    return None
            
            # Convert zone IDs to strings for logging
            zone_preview = ', '.join(str(z) for z in zones_to_query[:5])
            self.log_message(
                f"Found {len(zones_to_query)} zones to query: {zone_preview}...",
                Qgis.Info
            )
            
            # Combine features from all zones
            all_features = []
            
            for zone in zones_to_query:
                zone_data = self.query_zone_data(zone, dggs_crs)
                if zone_data and 'features' in zone_data:
                    all_features.extend(zone_data['features'])
            
            # Create combined FeatureCollection
            result = {
                "type": "FeatureCollection",
                "features": all_features
            }
            
            self.last_response = result
            self.last_error = None
            
            self.log_message(
                f"Successfully retrieved {len(all_features)} features from {len(zones_to_query)} zones",
                Qgis.Success
            )
            
            return result
                
        except urllib.error.HTTPError as e:
            error_body = ""
            try:
                error_body = e.read().decode('utf-8')
            except:
                pass
            
            error_msg = f"HTTP Error {e.code}: {e.reason}"
            if error_body:
                error_msg += f"\nDetails: {error_body[:200]}"
            
            if e.code == 400:
                error_msg += "\n\nPossible causes:\n"
                error_msg += "- Bounding box too large (try a smaller area)\n"
                error_msg += "- Invalid DGGS CRS parameter\n"
                error_msg += "- Invalid zone ID"
            
            self.last_error = error_msg
            self.log_message(error_msg, Qgis.Critical)
            return None
            
        except urllib.error.URLError as e:
            error_msg = f"URL Error: {e.reason}"
            self.last_error = error_msg
            self.log_message(error_msg, Qgis.Critical)
            return None
            
        except json.JSONDecodeError as e:
            error_msg = f"JSON Decode Error: {str(e)}"
            self.last_error = error_msg
            self.log_message(error_msg, Qgis.Critical)
            return None
            
        except Exception as e:
            error_msg = f"Unexpected error: {str(e)}"
            self.last_error = error_msg
            self.log_message(error_msg, Qgis.Critical)
            return None
    
    def query_zone_data(self, zone_id, dggs_crs="rHEALPix"):
        """
        Query data for a specific DGGS zone
        
        Args:
            zone_id: DGGS zone identifier (e.g., 'P44', 'O01')
            dggs_crs: DGGS system name
            
        Returns:
            dict: GeoJSON data for the zone or None if error
        """
        try:
            # Ensure zone_id is a string
            zone_id_str = str(zone_id)
            
            # Build zone data URL
            url = f"{self.BASE_URL}/collections/{self.COLLECTION}/dggs/{dggs_crs}/zones/{zone_id_str}/data.geojson"
            
            self.log_message(f"Querying zone {zone_id_str}: {url}", Qgis.Info)
            
            # Make request
            request = urllib.request.Request(url)
            request.add_header('Accept', 'application/json')
            
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
                result = json.loads(data.decode('utf-8'))
                return result
                
        except urllib.error.HTTPError as e:
            if e.code == 404:
                self.log_message(f"No data available for zone {zone_id_str}", Qgis.Warning)
            else:
                self.log_message(f"HTTP Error {e.code} for zone {zone_id_str}: {e.reason}", Qgis.Warning)
            return None
            
        except Exception as e:
            self.log_message(f"Error querying zone {zone_id_str}: {str(e)}", Qgis.Warning)
            return None
    
    def get_zones_for_extent(self, extent, dggs_crs="rHEALPix", zone_level=2):
        """
        Get list of DGGS zones that intersect with the extent
        
        Args:
            extent: QgsRectangle in EPSG:4326
            dggs_crs: DGGS system name
            zone_level: Zone resolution level (default: 2)
            
        Returns:
            list: List of zone IDs that intersect the extent
        """
        try:
            # Query zones metadata
            url = f"{self.BASE_URL}/collections/{self.COLLECTION}/dggs/{dggs_crs}/zones.geojson?zone-level={zone_level}"
            
            self.log_message(f"Fetching zones list: {url}", Qgis.Info)
            
            request = urllib.request.Request(url)
            request.add_header('Accept', 'application/json')
            
            with urllib.request.urlopen(request, timeout=30) as response:
                data = response.read()
                zones_data = json.loads(data.decode('utf-8'))
            
            # Filter zones that intersect with the extent
            matching_zones = []
            
            for feature in zones_data.get('features', []):
                zone_id = feature.get('id')
                if not zone_id:
                    continue
                
                # Get zone bbox from properties or geometry
                props = feature.get('properties', {})
                
                # Try to extract zone bounds
                zone_min_lat = props.get('min_lat') or props.get('min_latitude')
                zone_max_lat = props.get('max_lat') or props.get('max_latitude')
                zone_min_lon = props.get('min_lon') or props.get('min_longitude')
                zone_max_lon = props.get('max_lon') or props.get('max_longitude')
                
                # If bounds are available, check intersection
                if all([zone_min_lat, zone_max_lat, zone_min_lon, zone_max_lon]):
                    # Check if zones intersect
                    if not (extent.xMaximum() < zone_min_lon or 
                            extent.xMinimum() > zone_max_lon or
                            extent.yMaximum() < zone_min_lat or 
                            extent.yMinimum() > zone_max_lat):
                        matching_zones.append(zone_id)
                else:
                    # If no bounds info, include the zone (safer approach)
                    matching_zones.append(zone_id)
            
            self.log_message(f"Found {len(matching_zones)} matching zones", Qgis.Info)
            return matching_zones
            
        except Exception as e:
            error_msg = f"Error fetching zones list: {str(e)}"
            self.log_message(error_msg, Qgis.Critical)
            return []
    
    def get_dggs_zones_for_extent(self, extent, dggs_crs="rHEALPix-R12"):
        """
        Get all DGGS zones that intersect with the given extent
        
        Args:
            extent: QgsRectangle in EPSG:4326
            dggs_crs: DGGS CRS identifier
            
        Returns:
            list: List of zone IDs or empty list if error
        """
        result = self.query_dggs_data(extent, dggs_crs)
        
        if not result:
            return []
        
        # Extract unique zone IDs from features
        zone_ids = set()
        for feature in result.get('features', []):
            if 'properties' in feature:
                zone_id = feature['properties'].get('dggs_zone_id') or \
                         feature['properties'].get('zone_id') or \
                         feature.get('id')
                if zone_id:
                    zone_ids.add(zone_id)
        
        return sorted(list(zone_ids))
    
    def transform_extent_to_wgs84(self, extent, source_crs):
        """
        Transform extent to WGS84 (EPSG:4326) if needed
        
        Args:
            extent: QgsRectangle in source CRS
            source_crs: QgsCoordinateReferenceSystem of the extent
            
        Returns:
            QgsRectangle in EPSG:4326
        """
        if source_crs.authid() == 'EPSG:4326':
            return extent
        
        transform = QgsCoordinateTransform(
            source_crs,
            QgsCoordinateReferenceSystem('EPSG:4326'),
            QgsProject.instance()
        )
        
        return transform.transformBoundingBox(extent)
    
    def get_coverage_summary(self, extent, dggs_crs="rHEALPix-R12"):
        """
        Get a summary of SRTM coverage for the given extent
        
        Args:
            extent: QgsRectangle in EPSG:4326
            dggs_crs: DGGS CRS identifier
            
        Returns:
            dict: Summary with zone count, coverage info, etc.
        """
        result = self.query_dggs_data(extent, dggs_crs)
        
        if not result:
            return {
                'success': False,
                'error': self.last_error,
                'zone_count': 0,
                'feature_count': 0
            }
        
        features = result.get('features', [])
        zone_ids = self.get_dggs_zones_for_extent(extent, dggs_crs)
        
        # Extract elevation statistics if available
        elevations = []
        for feature in features:
            props = feature.get('properties', {})
            if 'elevation' in props:
                elevations.append(props['elevation'])
            elif 'height' in props:
                elevations.append(props['height'])
        
        summary = {
            'success': True,
            'error': None,
            'zone_count': len(zone_ids),
            'feature_count': len(features),
            'zones': zone_ids,
            'dggs_crs': dggs_crs,
            'extent': {
                'xmin': extent.xMinimum(),
                'ymin': extent.yMinimum(),
                'xmax': extent.xMaximum(),
                'ymax': extent.yMaximum()
            }
        }
        
        if elevations:
            summary['elevation_stats'] = {
                'min': min(elevations),
                'max': max(elevations),
                'count': len(elevations)
            }
        
        return summary
    
    def fetch_and_save_geojson(self, extent, output_path, dggs_crs="rHEALPix-R12", zone_id=None):
        """
        Fetch DGGS data and save as GeoJSON file
        
        Args:
            extent: QgsRectangle in EPSG:4326
            output_path: Path where to save the GeoJSON file
            dggs_crs: DGGS CRS identifier
            zone_id: Optional specific zone ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        result = self.query_dggs_data(extent, dggs_crs, zone_id)
        
        if not result:
            return False
        
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)
            
            self.log_message(f"Saved DGGS data to {output_path}", Qgis.Success)
            return True
            
        except Exception as e:
            error_msg = f"Error saving GeoJSON: {str(e)}"
            self.last_error = error_msg
            self.log_message(error_msg, Qgis.Critical)
            return False
    
    def log_message(self, message, level=Qgis.Info):
        """
        Log a message to QGIS message log
        
        Args:
            message: Message to log
            level: Message level (Info, Warning, Critical, Success)
        """
        QgsMessageLog.logMessage(message, 'GNOSIS DGGS Agent', level)
    
    def get_available_dggs_crs_list(self):
        """
        Get list of available DGGS CRS options
        
        Returns:
            list: Available DGGS CRS identifiers
        """
        # Common DGGS CRS options
        return [
            "rHEALPix-R12",
            "rHEALPix-R10",
            "rHEALPix-R8",
            "ISEA3H",
            "H3"
        ]
