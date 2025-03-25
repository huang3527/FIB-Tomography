import sys
from PySide6 import QtWidgets, QtCore
import vtk
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("FIB Tomo GUI with Volume Rendering and Sliders")
        
        # Set up the central widget and layout
        central_widget = QtWidgets.QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QtWidgets.QVBoxLayout(central_widget)
        
        # Create and add the VTK widget
        self.vtkWidget = QVTKRenderWindowInteractor(central_widget)
        main_layout.addWidget(self.vtkWidget)
        
        # Create a horizontal layout for sliders (example: camera Z position)
        slider_layout = QtWidgets.QHBoxLayout()
        main_layout.addLayout(slider_layout)
        
        # Label for the slider
        label = QtWidgets.QLabel("Camera Z Position:")
        slider_layout.addWidget(label)
        
        # Create a slider for controlling the camera's Z coordinate
        self.camera_z_slider = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.camera_z_slider.setMinimum(0)
        self.camera_z_slider.setMaximum(10000)   # Adjust range based on your data
        self.camera_z_slider.setValue(3681)        # Initial value from your setup (750,363,3681)
        self.camera_z_slider.valueChanged.connect(self.update_camera_z)
        slider_layout.addWidget(self.camera_z_slider)
        
        # Set up the VTK renderer, render window, and interactor
        self.renderer = vtk.vtkRenderer()
        render_window = self.vtkWidget.GetRenderWindow()
        render_window.AddRenderer(self.renderer)
        self.interactor = render_window.GetInteractor()
        
        # Set up the volume rendering pipeline
        self.setupVolumeRendering()
        
        # Set custom camera parameters (using your initial values)
        self.camera = self.renderer.GetActiveCamera()
        self.camera.SetPosition(750, 363, 3681)
        self.camera.SetFocalPoint(750, 363, 24.5)
        self.camera.SetViewUp(0, 1, 0)
        self.renderer.ResetCameraClippingRange()
        
        # Start the interactor
        self.interactor.Initialize()
        self.interactor.Start()
    
    def setupVolumeRendering(self):
        # Load the volume data (adjust the reader and file path for your data)
        reader = vtk.vtkMetaImageReader()
        reader.SetFileName("path_to_volume_data.mha")
        reader.Update()
        
        # Create a GPU volume mapper for interactive rendering
        volumeMapper = vtk.vtkGPUVolumeRayCastMapper()
        volumeMapper.SetInputConnection(reader.GetOutputPort())
        
        # Configure the color transfer function
        volumeColor = vtk.vtkColorTransferFunction()
        volumeColor.AddRGBPoint(0, 0.0, 0.0, 0.0)
        volumeColor.AddRGBPoint(500, 1.0, 0.5, 0.3)
        volumeColor.AddRGBPoint(1000, 1.0, 0.5, 0.3)
        volumeColor.AddRGBPoint(1150, 1.0, 1.0, 0.9)
        
        # Configure the opacity transfer function
        volumeScalarOpacity = vtk.vtkPiecewiseFunction()
        volumeScalarOpacity.AddPoint(0, 0.00)
        volumeScalarOpacity.AddPoint(500, 0.15)
        volumeScalarOpacity.AddPoint(1000, 0.15)
        volumeScalarOpacity.AddPoint(1150, 0.85)
        
        # Create and configure the volume property
        volumeProperty = vtk.vtkVolumeProperty()
        volumeProperty.SetColor(volumeColor)
        volumeProperty.SetScalarOpacity(volumeScalarOpacity)
        volumeProperty.ShadeOn()
        volumeProperty.SetInterpolationTypeToLinear()
        
        # Create the volume actor, add the mapper and property, then add to the renderer
        volume = vtk.vtkVolume()
        volume.SetMapper(volumeMapper)
        volume.SetProperty(volumeProperty)
        self.renderer.AddVolume(volume)
        
        # Set a background color and adjust the camera
        self.renderer.SetBackground(0.1, 0.2, 0.4)
        self.renderer.ResetCamera()
    
    def update_camera_z(self, value):
        # Update the camera's Z coordinate based on the slider value
        pos = list(self.camera.GetPosition())
        pos[2] = value
        self.camera.SetPosition(pos)
        self.renderer.ResetCameraClippingRange()
        self.vtkWidget.GetRenderWindow().Render()

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())