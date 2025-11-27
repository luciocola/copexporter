"""
COP STAC Dialog - UI for layer selection and export configuration
"""
import os
import math
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from qgis.core import (
    QgsProject, 
    QgsVectorLayer, 
    QgsRasterLayer,
    QgsCoordinateReferenceSystem,
    QgsCoordinateTransform
)
from .stac_cop_exporter import STACCOPExporter

# Load UI file
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'cop_stac_dialog.ui'))


class COPSTACDialog(QDialog, FORM_CLASS):
    """Dialog for COP STAC Export configuration"""

    def __init__(self, iface=None, parent=None):
        """Constructor."""
        super(COPSTACDialog, self).__init__(parent)
        self.setupUi(self)
        self.iface = iface
        
        # Connect signals
        self.btnSelectOutput.clicked.connect(self.select_output_directory)
        self.btnSelectAll.clicked.connect(self.select_all_layers)
        self.btnDeselectAll.clicked.connect(self.deselect_all_layers)
        self.btnExport.clicked.connect(self.export_layers)
        self.btnCancel.clicked.connect(self.reject)
        self.comboDGGSCRS.currentIndexChanged.connect(self.update_dggs_zone_id)
        self.listLayers.itemChanged.connect(self.update_dggs_zone_id)
        
        # Initialize
        self.output_dir = None
        self.load_layers()
        self.set_default_values()
        self.update_dggs_zone_id()

    def load_layers(self):
        """Load only visible layers from map canvas into the list widget"""
        self.listLayers.clear()
        project = QgsProject.instance()
        root = project.layerTreeRoot()
        
        # Get only visible layers from layer tree
        for layer in root.findLayers():
            if layer.isVisible():
                map_layer = layer.layer()
                # Add layer to list with checkbox
                from qgis.PyQt.QtWidgets import QListWidgetItem
                from qgis.PyQt.QtCore import Qt
                
                item = QListWidgetItem(map_layer.name())
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked)
                item.setData(Qt.UserRole, map_layer.id())
                self.listLayers.addItem(item)

    def select_all_layers(self):
        """Select all layers in the list"""
        from qgis.PyQt.QtCore import Qt
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            item.setCheckState(Qt.Checked)

    def deselect_all_layers(self):
        """Deselect all layers in the list"""
        from qgis.PyQt.QtCore import Qt
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            item.setCheckState(Qt.Unchecked)

    def select_output_directory(self):
        """Open dialog to select output directory"""
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            os.path.expanduser("~")
        )
        if directory:
            self.output_dir = directory
            self.lineOutputDir.setText(directory)

    def set_default_values(self):
        """Set default values for COP fields"""
        self.comboClassification.setCurrentText("public release")
        self.lineReleasability.setText("1:N")
        self.comboDGGSCRS.setCurrentIndex(0)  # rHEALPix
        self.checkCreateZip.setChecked(True)

    def update_dggs_zone_id(self):
        """Calculate and update DGGS zone ID based on selected layers extent"""
        selected_layers = self.get_selected_layers()
        if not selected_layers:
            self.lineDGGSZone.setText("")
            return
        
        # Calculate combined extent of all selected layers
        project = QgsProject.instance()
        combined_extent = None
        
        for layer in selected_layers:
            extent = layer.extent()
            crs = layer.crs()
            
            # Transform to WGS84 if needed
            if crs.authid() != 'EPSG:4326':
                transform = QgsCoordinateTransform(
                    crs,
                    QgsCoordinateReferenceSystem('EPSG:4326'),
                    project
                )
                extent = transform.transformBoundingBox(extent)
            
            if combined_extent is None:
                combined_extent = extent
            else:
                combined_extent.combineExtentWith(extent)
        
        if combined_extent is None:
            self.lineDGGSZone.setText("")
            return
        
        # Calculate center point
        center_lon = (combined_extent.xMinimum() + combined_extent.xMaximum()) / 2
        center_lat = (combined_extent.yMinimum() + combined_extent.yMaximum()) / 2
        
        # Get selected DGGS CRS
        dggs_crs = self.comboDGGSCRS.currentText()
        
        # Calculate zone ID based on DGGS type
        zone_id = self.calculate_dggs_zone_id(dggs_crs, center_lat, center_lon, combined_extent)
        self.lineDGGSZone.setText(zone_id)
    
    def calculate_dggs_zone_id(self, dggs_crs, lat, lon, extent):
        """Calculate DGGS zone ID based on CRS type and coordinates"""
        if "rHEALPix" in dggs_crs:
            # rHEALPix zone calculation (simplified)
            resolution = 12  # Default resolution
            # Calculate cell ID based on lat/lon
            # This is a simplified example - real implementation would use rhealpix library
            lat_zone = int((lat + 90) / 15)  # 12 zones vertically
            lon_zone = int((lon + 180) / 30)  # 12 zones horizontally
            return f"R{lat_zone:02d}_{lon_zone:02d}"
        
        elif dggs_crs == "H3":
            # H3 uses hexagonal cells - calculate approximate resolution 5 cell
            # This is simplified - real implementation would use h3 library
            resolution = 5
            # Approximate H3 cell (this is just for demonstration)
            return f"85{abs(int(lat * 1000000)):07d}{abs(int(lon * 1000000)):07d}"
        
        elif dggs_crs == "S2":
            # S2 geometry - uses hierarchical cells
            # This is simplified - real implementation would use s2geometry library
            level = 10
            return f"S2_{abs(int(lat * 10000)):06d}_{abs(int(lon * 10000)):06d}"
        
        elif dggs_crs == "ISEA3H":
            # ISEA3H (Icosahedral Snyder Equal Area) 
            resolution = 12
            face = int((lon + 180) / 72)  # 5 faces
            return f"ISEA3H_F{face}_R{resolution}"
        
        elif dggs_crs == "IGEO":
            # IGEO (Icosahedral Global Equal-area Octree)
            resolution = 10
            zone = int((lon + 180) / 36)  # 10 zones
            return f"IGEO_Z{zone:02d}_R{resolution}"
        
        else:
            return "AUTO"
    
    def get_dggs_crs_string(self):
        """Get DGGS CRS string for metadata"""
        dggs_text = self.comboDGGSCRS.currentText()
        
        # Map UI text to standard DGGS CRS identifiers
        dggs_map = {
            "rHEALPix (EPSG:4326)": "rHEALPix-R12",
            "H3": "H3-R5",
            "S2": "S2-L10",
            "ISEA3H": "ISEA3H-R12",
            "IGEO": "IGEO-R10"
        }
        
        return dggs_map.get(dggs_text, "rHEALPix-R12")
    
    def get_selected_layers(self):
        """Get list of selected layer IDs"""
        from qgis.PyQt.QtCore import Qt
        selected = []
        project = QgsProject.instance()
        
        for i in range(self.listLayers.count()):
            item = self.listLayers.item(i)
            if item.checkState() == Qt.Checked:
                layer_id = item.data(Qt.UserRole)
                layer = project.mapLayer(layer_id)
                if layer:
                    selected.append(layer)
        
        return selected

    def export_layers(self):
        """Export selected layers to STAC COP format"""
        # Validate inputs
        if not self.output_dir:
            QMessageBox.warning(
                self,
                "Missing Output Directory",
                "Please select an output directory."
            )
            return

        selected_layers = self.get_selected_layers()
        if not selected_layers:
            QMessageBox.warning(
                self,
                "No Layers Selected",
                "Please select at least one layer to export."
            )
            return

        # Get COP metadata
        cop_metadata = {
            'mission': self.lineMission.text(),
            'classification': self.comboClassification.currentText(),
            'releasability': self.lineReleasability.text(),
            'dggs_crs': self.get_dggs_crs_string(),
            'dggs_zone_id': self.lineDGGSZone.text(),
            'service_provider': self.lineServiceProvider.text()
        }

        # Export layers
        try:
            # Get map canvas for raster extent if available
            map_canvas = self.iface.mapCanvas() if self.iface else None
            exporter = STACCOPExporter(self.output_dir, map_canvas=map_canvas)
            success_count = 0
            
            for layer in selected_layers:
                try:
                    exporter.export_layer(layer, cop_metadata)
                    success_count += 1
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        f"Export Error - {layer.name()}",
                        f"Failed to export layer: {str(e)}"
                    )

            # Create ZIP if requested
            if self.checkCreateZip.isChecked() and success_count > 0:
                zip_path, sha256_hash = exporter.create_zip_archive()
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Successfully exported {success_count} layer(s).\n\n"
                    f"ZIP archive created at:\n{zip_path}\n\n"
                    f"SHA256: {sha256_hash}"
                )
            elif success_count > 0:
                QMessageBox.information(
                    self,
                    "Export Complete",
                    f"Successfully exported {success_count} layer(s) to:\n{self.output_dir}"
                )

            if success_count > 0:
                self.accept()

        except Exception as e:
            QMessageBox.critical(
                self,
                "Export Error",
                f"An error occurred during export:\n{str(e)}"
            )
