from PySide6.QtWidgets import QWidget, QVBoxLayout
from pyvistaqt import QtInteractor
import pyvista as pv
import numpy as np


class VisualizationView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create the main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.plotter = QtInteractor(self)
        layout.addWidget(self.plotter)

        # Set up the initial visualization environment
        self._setup_visualization()

    def _setup_visualization(self):
        self.plotter.set_background("black")
        self.plotter.add_axes(xlabel="X", ylabel="Y", zlabel="Z")

        # Create a reference grid (100mm x 100mm, 10mm spacing)
        grid = pv.Plane(
            center=(0, 0, 0),
            direction=(0, 0, 1),
            i_size=100,  # Total size in mm (X-axis)
            j_size=100,  # Total size in mm (Y-axis)
            i_resolution=10,  # 10mm spacing between grid lines
            j_resolution=10,
        )
        self.plotter.add_mesh(
            grid, color="gray", opacity=0.5, show_edges=True, edge_color="black"
        )

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
        """Clear all visualized positions"""
        self.plotter.clear()
        self._setup_visualization()  # Reset the basic environment

    def closeEvent(self, event):
        """Properly clean up resources when closing"""
        self.plotter.close()
        super().closeEvent(event)
