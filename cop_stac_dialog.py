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
from .gnosis_dggs_agent import GnosisDGGSAgent

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
        
        # Connect GNOSIS query button if it exists in UI
        if hasattr(self, 'btnQueryGnosis'):
            self.btnQueryGnosis.clicked.connect(self.query_gnosis_earth)
        
        # Initialize GNOSIS agent
        self.gnosis_agent = GnosisDGGSAgent()
        self.gnosis_data_path = None  # Store path to GNOSIS data for export
        self.export_extent = None  # Store map canvas extent for clipping exports
        
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
        """Get DGGS CRS string for metadata and API"""
        dggs_text = self.comboDGGSCRS.currentText()
        
        # Map UI text to GNOSIS API DGGS system names
        dggs_map = {
            "rHEALPix (EPSG:4326)": "rHEALPix",
            "H3": "H3",
            "S2": "S2",
            "ISEA3H": "ISEA3H",
            "IGEO": "IGEO"
        }
        
        return dggs_map.get(dggs_text, "rHEALPix")
    
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

    def query_gnosis_earth(self):
        """Query GNOSIS Earth API for SRTM data in current map view extent"""
        # Get current map canvas extent
        if not self.iface:
            QMessageBox.warning(
                self,
                "No Map Canvas",
                "Cannot access map canvas. Please ensure QGIS interface is available."
            )
            return
        
        canvas = self.iface.mapCanvas()
        extent = canvas.extent()
        canvas_crs = canvas.mapSettings().destinationCrs()
        
        # Transform to WGS84
        combined_extent = self.gnosis_agent.transform_extent_to_wgs84(extent, canvas_crs)
        
        if combined_extent is None:
            QMessageBox.warning(self, "Error", "Could not determine extent.")
            return
        
        # Validate extent is not too large
        extent_width = combined_extent.xMaximum() - combined_extent.xMinimum()
        extent_height = combined_extent.yMaximum() - combined_extent.yMinimum()
        
        if extent_width > 180 or extent_height > 90:
            QMessageBox.warning(
                self,
                "Extent Too Large",
                f"The query extent is too large ({extent_width:.2f}° x {extent_height:.2f}°).\n\n"
                "GNOSIS Earth API requires a more specific area.\n"
                "Please select layers with a smaller geographic extent (max 180° x 90°)."
            )
            return
        
        # Clamp extent to valid WGS84 bounds
        combined_extent.set(
            max(-180.0, combined_extent.xMinimum()),
            max(-85.0511, combined_extent.yMinimum()),
            min(180.0, combined_extent.xMaximum()),
            min(85.0511, combined_extent.yMaximum())
        )
        
        # Get DGGS CRS
        dggs_crs = self.get_dggs_crs_string()
        zone_id = self.lineDGGSZone.text() if self.lineDGGSZone.text() else None
        
        # Show progress message
        from qgis.PyQt.QtWidgets import QProgressDialog
        from qgis.PyQt.QtCore import Qt
        
        progress = QProgressDialog("Querying GNOSIS Earth API...", "Cancel", 0, 0, self)
        progress.setWindowModality(Qt.WindowModal)
        progress.setWindowTitle("GNOSIS DGGS Query")
        progress.show()
        
        try:
            # Query GNOSIS Earth
            summary = self.gnosis_agent.get_coverage_summary(combined_extent, dggs_crs)
            
            progress.close()
            
            if not summary['success']:
                QMessageBox.critical(
                    self,
                    "Query Failed",
                    f"Failed to query GNOSIS Earth API:\n{summary.get('error', 'Unknown error')}"
                )
                return
            
            # Build result message
            result_msg = f"<h3>GNOSIS Earth SRTM Coverage</h3>"
            result_msg += f"<p><b>DGGS CRS:</b> {summary['dggs_crs']}</p>"
            result_msg += f"<p><b>DGGS Zones Found:</b> {summary['zone_count']}</p>"
            result_msg += f"<p><b>Features Found:</b> {summary['feature_count']}</p>"
            
            if summary.get('zones'):
                zones_list = ', '.join(summary['zones'][:10])
                if len(summary['zones']) > 10:
                    zones_list += f" ... (+{len(summary['zones']) - 10} more)"
                result_msg += f"<p><b>Zone IDs:</b> {zones_list}</p>"
            
            if 'elevation_stats' in summary:
                elev = summary['elevation_stats']
                result_msg += f"<p><b>Elevation Range:</b> {elev['min']}m to {elev['max']}m</p>"
            
            result_msg += f"<hr><p><b>Extent:</b><br>"
            result_msg += f"Lon: {summary['extent']['xmin']:.4f} to {summary['extent']['xmax']:.4f}<br>"
            result_msg += f"Lat: {summary['extent']['ymin']:.4f} to {summary['extent']['ymax']:.4f}</p>"
            # Ask if user wants to include the data in export
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("GNOSIS Earth Query Results")
            msg_box.setTextFormat(Qt.RichText)
            msg_box.setText(result_msg)
            msg_box.setInformativeText("Include this SRTM elevation data in the COP STAC export?")
            msg_box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
            msg_box.setDefaultButton(QMessageBox.Yes)
            
            if msg_box.exec_() == QMessageBox.Yes:
                # Automatically save to temp location for export
                self.auto_save_gnosis_data(combined_extent, dggs_crs, zone_id, summary)
                self.save_gnosis_data(combined_extent, dggs_crs, zone_id)
        
        except Exception as e:
            progress.close()
            QMessageBox.critical(
                self,
                "Query Error",
                f"Error querying GNOSIS Earth:\n{str(e)}"
            )
    def auto_save_gnosis_data(self, extent, dggs_crs, zone_id, summary):
        """Automatically save GNOSIS data for inclusion in COP export"""
        import tempfile
        
        # Create temp file for GNOSIS data
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, "gnosis_srtm_dggs_temp.geojson")
        
        # Fetch and save data
        success = self.gnosis_agent.fetch_and_save_geojson(
            extent, temp_file, dggs_crs, zone_id
        )
        
        if success:
            self.gnosis_data_path = temp_file
            
            # Add to map for visualization
            if self.iface:
                layer = QgsVectorLayer(temp_file, "GNOSIS SRTM DGGS", "ogr")
                if layer.isValid():
                    QgsProject.instance().addMapLayer(layer)
            
            # Show confirmation
            QMessageBox.information(
                self,
                "GNOSIS Data Ready",
                f"SRTM elevation data will be included in the COP export.\n\n"
                f"Zones: {summary['zone_count']}\n"
                f"Features: {summary['feature_count']}\n\n"
                f"The data has been added to the map for preview."
            )
        else:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save GNOSIS data:\n{self.gnosis_agent.last_error}"
            )
    
    def save_gnosis_data(self, extent, dggs_crs, zone_id=None):
        """Save GNOSIS Earth data as GeoJSON file and optionally add to map"""
        from qgis.PyQt.QtWidgets import QFileDialog
        
        # Ask for output file
        output_file, _ = QFileDialog.getSaveFileName(
            self,
            "Save GNOSIS Earth Data",
            os.path.join(os.path.expanduser("~"), "gnosis_srtm_dggs.geojson"),
            "GeoJSON (*.geojson *.json)"
        )
        
        if not output_file:
            return
        
        # Fetch and save data
        success = self.gnosis_agent.fetch_and_save_geojson(
            extent, output_file, dggs_crs, zone_id
        )
        
        if success:
            # Ask if user wants to add to map
            reply = QMessageBox.question(
                self,
                "Add to Map",
                "Data saved successfully. Add layer to map?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes and self.iface:
                layer = QgsVectorLayer(output_file, "GNOSIS SRTM DGGS", "ogr")
                if layer.isValid():
                    QgsProject.instance().addMapLayer(layer)
                    QMessageBox.information(
                        self,
                        "Success",
                        "Layer added to map successfully."
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Layer Error",
                        "Could not add layer to map."
                    )
        else:
            QMessageBox.critical(
                self,
                "Save Error",
                f"Failed to save data:\n{self.gnosis_agent.last_error}"
            )

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
            # Get map canvas extent for clipping if available
            map_canvas = self.iface.mapCanvas() if self.iface else None
            exporter = STACCOPExporter(self.output_dir, map_canvas=map_canvas)
            
            # Set clip extent from current map view
            if map_canvas:
                canvas_extent = map_canvas.extent()
                canvas_crs = map_canvas.mapSettings().destinationCrs()
                exporter.set_clip_extent(canvas_extent, canvas_crs)
            
            success_count = 0
            
            # Export selected layers
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
            
            # Export GNOSIS data if available
            if self.gnosis_data_path and os.path.exists(self.gnosis_data_path):
                try:
                    # Load GNOSIS data as a temporary layer
                    gnosis_layer = QgsVectorLayer(self.gnosis_data_path, "GNOSIS_SRTM_DGGS", "ogr")
                    if gnosis_layer.isValid():
                        # Add GNOSIS-specific metadata
                        gnosis_metadata = cop_metadata.copy()
                        gnosis_metadata['gnosis_source'] = 'GNOSIS Earth SRTM ViewFinder Panorama'
                        gnosis_metadata['data_type'] = 'elevation'
                        
                        exporter.export_layer(gnosis_layer, gnosis_metadata)
                        success_count += 1
                        
                        # Clean up temp file after export
                        # (keeping it for now in case user wants to reference it)
                except Exception as e:
                    QMessageBox.warning(
                        self,
                        "GNOSIS Export Warning",
                        f"Could not export GNOSIS data: {str(e)}"
                    )

            # Create STAC collection after all items are exported
            if success_count > 0:
                collection_id = cop_metadata.get('mission', 'cop-collection').lower().replace(' ', '-')
                exporter.create_collection(
                    collection_id=collection_id,
                    title=f"{cop_metadata.get('mission', 'COP Export')} Collection",
                    description=f"STAC Collection for {cop_metadata.get('mission', 'COP export')} with {success_count} item(s). Classification: {cop_metadata.get('classification', 'unknown')}."
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
