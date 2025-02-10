from PySide6.QtWidgets import QWidget, QVBoxLayout
from pyvistaqt import QtInteractor
import pyvista as pv
import numpy as np
from measurement_module.models.point_cloud_visualizer import PointCloudVisualizer

class VisualizationView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create the main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)


        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter)


        self.point_cloud_vis = PointCloudVisualizer(self.plotter)
        self._setup_visualization()

    def _setup_visualization(self):
        self.plotter.set_background("gray")
        self.plotter.add_axes(xlabel="X", ylabel="Y", zlabel="Z")

        self.plotter.add_floor(color="gray", opacity=0.5, show_edges=True, edge_color="black", line_width=2)

        self.plotter.camera_position = [
            (100, 100, 100),  # Camera position
            (0, 0, 0),  # Focal point
            (0, 0, 1),  # View up vector
        ]

        self.plotter.camera_position = "iso"
        self.plotter.camera.elevation = -15
        self.plotter.camera.azimuth = 45

        self.plotter.enable_trackball_style()

    def add_catheter_position(self, position, color="red"):
        sphere = pv.Sphere(radius=2, center=position)
        self.plotter.add_mesh(sphere, color=color)

    def clear_positions(self):
        self.plotter.clear()
        self._setup_visualization()  # Reset the basic environment

    def closeEvent(self, event):
        self.plotter.close()
        super().closeEvent(event)

    def update_point_cloud(self, frames):
        self.point_cloud_vis.update_visualization(frames)

    def clear_point_cloud(self):
        self.point_cloud_vis.clear()