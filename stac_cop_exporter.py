"""
STAC COP Exporter - Core export functionality
"""
import hashlib
import json
import os
import uuid
import zipfile
from datetime import datetime, timezone
from qgis.core import (
    QgsVectorLayer,
    QgsRasterLayer,
    QgsVectorFileWriter,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform,
    QgsProject
)


class STACCOPExporter:
    """Handles export of QGIS layers to STAC format with COP extension"""

    def __init__(self, output_dir):
        """
        Initialize exporter
        
        Args:
            output_dir: Directory where STAC files will be exported
        """
        self.output_dir = output_dir
        self.exported_items = []
        
        # Create STAC collection directory
        self.stac_dir = os.path.join(output_dir, 'stac_cop_export')
        os.makedirs(self.stac_dir, exist_ok=True)
        
        # Create assets directory
        self.assets_dir = os.path.join(self.stac_dir, 'assets')
        os.makedirs(self.assets_dir, exist_ok=True)

    def export_layer(self, layer, cop_metadata):
        """
        Export a single QGIS layer to STAC COP format
        
        Args:
            layer: QgsMapLayer to export
            cop_metadata: Dictionary containing COP metadata fields
        """
        layer_name = layer.name()
        # Generate UUID4 for STAC item ID
        layer_id = str(uuid.uuid4())
        # Use sanitized name for file naming
        file_name = self.sanitize_id(layer_name)
        
        # Export layer data
        asset_path = self.export_layer_data(layer, file_name)
        
        # Create STAC Item
        stac_item = self.create_stac_item(layer, layer_id, asset_path, cop_metadata)
        
        # Save STAC Item JSON using sanitized filename
        item_path = os.path.join(self.stac_dir, f'{file_name}.json')
        with open(item_path, 'w', encoding='utf-8') as f:
            json.dump(stac_item, f, indent=2)
        
        self.exported_items.append(stac_item)
        return item_path

    def export_layer_data(self, layer, layer_id):
        """
        Export layer data to file
        
        Args:
            layer: QgsMapLayer to export
            layer_id: Sanitized layer identifier
            
        Returns:
            Path to exported asset file
        """
        if isinstance(layer, QgsVectorLayer):
            # Export as GeoJSON
            output_file = os.path.join(self.assets_dir, f'{layer_id}.geojson')
            
            options = QgsVectorFileWriter.SaveVectorOptions()
            options.driverName = 'GeoJSON'
            options.fileEncoding = 'UTF-8'
            
            error = QgsVectorFileWriter.writeAsVectorFormatV3(
                layer,
                output_file,
                QgsProject.instance().transformContext(),
                options
            )
            
            if error[0] != QgsVectorFileWriter.NoError:
                raise Exception(f"Failed to export vector layer: {error}")
            
            return output_file
            
        elif isinstance(layer, QgsRasterLayer):
            # For raster, we'll reference the original source
            # In a production plugin, you'd want to copy/process the raster
            return layer.source()
        
        else:
            raise Exception(f"Unsupported layer type: {type(layer)}")

    def create_stac_item(self, layer, layer_id, asset_path, cop_metadata):
        """
        Create STAC Item with COP extension
        
        Args:
            layer: QgsMapLayer
            layer_id: Sanitized identifier
            asset_path: Path to exported asset
            cop_metadata: COP metadata dictionary
            
        Returns:
            STAC Item dictionary
        """
        # Get layer extent
        extent = layer.extent()
        crs = layer.crs()
        
        # Transform to WGS84 if needed
        if crs.authid() != 'EPSG:4326':
            transform = QgsCoordinateTransform(
                crs,
                QgsCoordinateReferenceSystem('EPSG:4326'),
                QgsProject.instance()
            )
            extent = transform.transformBoundingBox(extent)
        
        bbox = [
            extent.xMinimum(),
            extent.yMinimum(),
            extent.xMaximum(),
            extent.yMaximum()
        ]
        
        # Create geometry
        geometry = {
            "type": "Polygon",
            "coordinates": [[
                [extent.xMinimum(), extent.yMinimum()],
                [extent.xMaximum(), extent.yMinimum()],
                [extent.xMaximum(), extent.yMaximum()],
                [extent.xMinimum(), extent.yMaximum()],
                [extent.xMinimum(), extent.yMinimum()]
            ]]
        }
        
        # Determine asset type
        if isinstance(layer, QgsVectorLayer):
            asset_type = "feature"
            media_type = "application/geo+json"
            file_ext = os.path.splitext(asset_path)[1]
        else:
            asset_type = "imagery"
            media_type = "image/tiff"
            file_ext = os.path.splitext(asset_path)[1]
        
        # Build STAC Item
        stac_item = {
            "stac_version": "1.0.0",
            "stac_extensions": [
                "https://stac-extensions.github.io/cop/v1.0.0/schema.json"
            ],
            "type": "Feature",
            "id": layer_id,
            "bbox": bbox,
            "geometry": geometry,
            "properties": {
                "datetime": datetime.now(timezone.utc).isoformat(),
                "title": layer.name()
            },
            "assets": {
                "data": {
                    "href": os.path.relpath(asset_path, self.stac_dir),
                    "title": f"{layer.name()} Data",
                    "type": media_type,
                    "roles": ["data"],
                    "cop:asset_type": asset_type
                }
            },
            "links": [
                {
                    "rel": "self",
                    "href": f"./{layer_id}.json"
                }
            ]
        }
        
        # Add COP metadata fields to properties
        if cop_metadata.get('mission'):
            stac_item['properties']['cop:mission'] = cop_metadata['mission']
        
        if cop_metadata.get('classification'):
            stac_item['properties']['cop:classification'] = cop_metadata['classification']
        
        if cop_metadata.get('releasability'):
            stac_item['properties']['cop:releasability'] = cop_metadata['releasability']
        
        if cop_metadata.get('dggs_crs'):
            stac_item['properties']['cop:dggs_crs'] = cop_metadata['dggs_crs']
        
        if cop_metadata.get('dggs_zone_id'):
            stac_item['properties']['cop:dggs_zone_id'] = cop_metadata['dggs_zone_id']
        
        if cop_metadata.get('service_provider'):
            stac_item['properties']['cop:service_provider'] = cop_metadata['service_provider']
        
        return stac_item

    def create_collection(self, collection_id, title, description):
        """
        Create STAC Collection for exported items
        
        Args:
            collection_id: Collection identifier
            title: Collection title
            description: Collection description
            
        Returns:
            Path to collection JSON file
        """
        # Calculate overall extent from items
        all_bbox = []
        all_times = []
        
        for item in self.exported_items:
            all_bbox.append(item['bbox'])
            if 'datetime' in item['properties']:
                all_times.append(item['properties']['datetime'])
        
        # Calculate spatial extent
        if all_bbox:
            min_x = min(bbox[0] for bbox in all_bbox)
            min_y = min(bbox[1] for bbox in all_bbox)
            max_x = max(bbox[2] for bbox in all_bbox)
            max_y = max(bbox[3] for bbox in all_bbox)
            spatial_bbox = [min_x, min_y, max_x, max_y]
        else:
            spatial_bbox = [-180, -90, 180, 90]
        
        # Calculate temporal extent
        if all_times:
            temporal_interval = [[min(all_times), max(all_times)]]
        else:
            now = datetime.now(timezone.utc).isoformat()
            temporal_interval = [[now, now]]
        
        collection = {
            "stac_version": "1.0.0",
            "stac_extensions": [
                "https://stac-extensions.github.io/cop/v1.0.0/schema.json"
            ],
            "type": "Collection",
            "id": collection_id,
            "title": title,
            "description": description,
            "license": "proprietary",
            "extent": {
                "spatial": {
                    "bbox": [spatial_bbox]
                },
                "temporal": {
                    "interval": temporal_interval
                }
            },
            "links": [
                {
                    "rel": "self",
                    "href": "./collection.json"
                },
                {
                    "rel": "root",
                    "href": "./collection.json"
                }
            ]
        }
        
        # Add item links
        for item in self.exported_items:
            collection['links'].append({
                "rel": "item",
                "href": f"./{item['id']}.json"
            })
        
        # Save collection
        collection_path = os.path.join(self.stac_dir, 'collection.json')
        with open(collection_path, 'w', encoding='utf-8') as f:
            json.dump(collection, f, indent=2)
        
        return collection_path

    def create_zip_archive(self):
        """
        Create ZIP archive of all exported STAC files and generate SHA256 hash
        
        Returns:
            Tuple of (zip_path, sha256_hash)
        """
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        zip_filename = f'stac_cop_export_{timestamp}.zip'
        zip_path = os.path.join(self.output_dir, zip_filename)
        
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # Walk through STAC directory and add all files
            for root, dirs, files in os.walk(self.stac_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, self.output_dir)
                    zipf.write(file_path, arcname)
        
        # Calculate SHA256 hash of the ZIP file
        sha256_hash = hashlib.sha256()
        with open(zip_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                sha256_hash.update(chunk)
        
        hash_value = sha256_hash.hexdigest()
        
        # Write hash to a text file
        hash_filename = f'stac_cop_export_{timestamp}.zip.sha256'
        hash_path = os.path.join(self.output_dir, hash_filename)
        with open(hash_path, 'w') as f:
            f.write(f"{hash_value}  {zip_filename}\n")
        
        return zip_path, hash_value

    @staticmethod
    def sanitize_id(name):
        """
        Sanitize layer name to create valid STAC ID
        
        Args:
            name: Original layer name
            
        Returns:
            Sanitized identifier
        """
        # Remove special characters and spaces
        sanitized = ''.join(c if c.isalnum() or c in '-_' else '_' for c in name)
        # Ensure it starts with alphanumeric
        if not sanitized[0].isalnum():
            sanitized = 'item_' + sanitized
        return sanitized.lower()
