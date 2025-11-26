"""
COP STAC Dialog - UI for layer selection and export configuration
"""
import os
from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QFileDialog, QMessageBox
from qgis.core import QgsProject, QgsVectorLayer, QgsRasterLayer
from .stac_cop_exporter import STACCOPExporter

# Load UI file
FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ui', 'cop_stac_dialog.ui'))


class COPSTACDialog(QDialog, FORM_CLASS):
    """Dialog for COP STAC Export configuration"""

    def __init__(self, parent=None):
        """Constructor."""
        super(COPSTACDialog, self).__init__(parent)
        self.setupUi(self)
        
        # Connect signals
        self.btnSelectOutput.clicked.connect(self.select_output_directory)
        self.btnSelectAll.clicked.connect(self.select_all_layers)
        self.btnDeselectAll.clicked.connect(self.deselect_all_layers)
        self.btnExport.clicked.connect(self.export_layers)
        self.btnCancel.clicked.connect(self.reject)
        
        # Initialize
        self.output_dir = None
        self.load_layers()
        self.set_default_values()

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
        self.lineDGGSCRS.setText("rHEALPix-R12")
        self.checkCreateZip.setChecked(True)

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
            'dggs_crs': self.lineDGGSCRS.text(),
            'dggs_zone_id': self.lineDGGSZone.text(),
            'service_provider': self.lineServiceProvider.text()
        }

        # Export layers
        try:
            exporter = STACCOPExporter(self.output_dir)
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
