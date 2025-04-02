import sys
import math
import vtk
from PySide6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from FIB_Tomo import FIBTomo

class FIBTomoVTKApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Instantiate FIBTomo and load the TIFF stack.
        self.tomo = FIBTomo()
        self.tomo.load_image(r'./image_stack.tif')
        self.x_offset = 50
        self.y_offset = 50
        self.z_offset = 50
        self.tomo.update_slice(self.x_offset, self.y_offset, self.z_offset)
        
        # Create the QVTKRenderWindowInteractor widget.
        self.vtkWidget = QVTKRenderWindowInteractor(self)
        self.render_window = self.vtkWidget.GetRenderWindow()
        
        # Create two renderers:
        # renderer_slice for the slice view and renderer_volume for the volume rendering.
        self.renderer_slice = vtk.vtkRenderer()
        self.renderer_slice.SetViewport(0.0, 0.0, 0.5, 1.0)
        self.renderer_slice.SetBackground(0.1, 0.1, 0.2)
        
        self.renderer_volume = vtk.vtkRenderer()
        self.renderer_volume.SetViewport(0.5, 0.0, 1.0, 1.0)
        self.renderer_volume.SetBackground(0.2, 0.2, 0.4)
        
        self.render_window.AddRenderer(self.renderer_slice)
        self.render_window.AddRenderer(self.renderer_volume)
        
        # Create an image actor for the slice view.
        self.image_actor = vtk.vtkImageActor()  # Displays a slice from FIBTomo loaded via load_image.
        self.update_image_actor()
        self.renderer_slice.AddActor(self.image_actor)
        
        # Set up slider widgets for adjusting slice offsets (using VTK slider widgets).
        self.setup_slider_widgets()
        
        # Add a scale bar (line and text) to the slice renderer.
        self.add_scale_bar()
        self.renderer_slice.GetActiveCamera().AddObserver("ModifiedEvent", self.camera_modified_callback)
        
        # Create and add the volume actor to the volume renderer.
        self.volume_actor = self.get_volume_actor()
        self.renderer_volume.AddVolume(self.volume_actor)
        
        # Initially, set the view mode to Volume Rendering.
        self.update_view_mode("Volume Rendering")
        
        # Build the overall layout.
        layout = QVBoxLayout()
        # Create a select box (QComboBox) at the top for selecting the view mode.
        select_layout = QHBoxLayout()
        label = QLabel("Select view mode:")
        self.combo = QComboBox()
        self.combo.addItems(["Volume Rendering", "Slice View"])
        self.combo.setCurrentText("Volume Rendering")
        self.combo.currentTextChanged.connect(self.update_view_mode)
        select_layout.addWidget(label)
        select_layout.addWidget(self.combo)
        layout.addLayout(select_layout)
        
        # Add the VTK render window widget.
        layout.addWidget(self.vtkWidget)
        self.setLayout(layout)
        
        # Initialize and start the VTK interactor.
        self.vtkWidget.Initialize()
        self.vtkWidget.Start()
    
    def update_image_actor(self):
        """Retrieve the updated vtkImageData from FIBTomo and refresh the slice view actor."""
        vtk_image = self.tomo.get_vtk_image()
        self.image_actor.GetMapper().SetInputData(vtk_image)
        self.render_window.Render()
    
    def setup_slider_widgets(self):
        """Creates three vtkSliderWidgets (for X, Y, and Z offsets) and places them in the left viewport."""
        self.sliders = {}
        slider_names = ["X Offset", "Y Offset", "Z Offset"]
        initial_value = 50
        for i, name in enumerate(slider_names):
            rep = vtk.vtkSliderRepresentation2D()
            rep.SetMinimumValue(0)
            rep.SetMaximumValue(100)
            rep.SetValue(initial_value)
            rep.SetTitleText(name)
            # Position sliders on the left half.
            rep.GetPoint1Coordinate().SetCoordinateSystemToNormalizedDisplay()
            rep.GetPoint1Coordinate().SetValue(0.05, 0.1 + i * 0.1)
            rep.GetPoint2Coordinate().SetCoordinateSystemToNormalizedDisplay()
            rep.GetPoint2Coordinate().SetValue(0.25, 0.1 + i * 0.1)
            
            slider_widget = vtk.vtkSliderWidget()
            slider_widget.SetInteractor(self.vtkWidget)
            slider_widget.SetRepresentation(rep)
            slider_widget.SetAnimationModeToAnimate()
            slider_widget.EnabledOn()
            slider_widget.AddObserver("InteractionEvent", self.slider_callback)
            self.sliders[name] = slider_widget
    
    def update_view_mode(self, mode):
        """
        Updates the view mode by adjusting the viewports of the two renderers.
        If 'Volume Rendering' is selected, the volume renderer occupies the full window.
        If 'Slice View' is selected, the slice renderer occupies the full window.
        Also resets the camera of the active renderer.
        """
        if mode == "Volume Rendering":
            self.renderer_volume.SetViewport(0.0, 0.0, 1.0, 1.0)
            self.renderer_volume.ResetCamera()
            # Hide the slice renderer.
            self.renderer_slice.SetViewport(0, 0, 0, 0)
        elif mode == "Slice View":
            self.renderer_slice.SetViewport(0.0, 0.0, 1.0, 1.0)
            self.renderer_slice.ResetCamera()
            # Hide the volume renderer.
            self.renderer_volume.SetViewport(0, 0, 0, 0)
        self.render_window.Render()
    
    def slider_callback(self, obj, event):
        """
        Callback for slider widgets.
        Reads the slider value, updates the corresponding offset,
        and refreshes the slice view.
        """
        slider_widget = obj
        value = int(slider_widget.GetRepresentation().GetValue())
        name = slider_widget.GetRepresentation().GetTitleText()
        if name == "X Offset":
            self.tomo.x_offset = value
        elif name == "Y Offset":
            self.tomo.y_offset = value
        elif name == "Z Offset":
            self.tomo.z_offset = value
        self.tomo.update_slice(self.tomo.x_offset, self.tomo.y_offset, self.tomo.z_offset)
        self.update_image_actor()
    
    def add_scale_bar(self):
        """
        Adds a scale bar (line and text label) to the slice renderer.
        """
        self.scale_bar_points = vtk.vtkPoints()
        self.scale_bar_points.InsertNextPoint(0, 0, 0)
        self.scale_bar_points.InsertNextPoint(1, 0, 0)
        
        line = vtk.vtkLine()
        line.GetPointIds().SetId(0, 0)
        line.GetPointIds().SetId(1, 1)
        lines = vtk.vtkCellArray()
        lines.InsertNextCell(line)
        
        self.scale_bar_polydata = vtk.vtkPolyData()
        self.scale_bar_polydata.SetPoints(self.scale_bar_points)
        self.scale_bar_polydata.SetLines(lines)
        
        self.scale_bar_mapper = vtk.vtkPolyDataMapper2D()
        self.scale_bar_mapper.SetInputData(self.scale_bar_polydata)
        
        self.scale_bar_actor = vtk.vtkActor2D()
        self.scale_bar_actor.SetMapper(self.scale_bar_mapper)
        self.scale_bar_actor.GetProperty().SetColor(1.0, 1.0, 1.0)
        self.scale_bar_actor.GetProperty().SetLineWidth(4)
        self.renderer_slice.AddActor2D(self.scale_bar_actor)
        
        self.scale_bar_text = vtk.vtkTextActor()
        txtprop = self.scale_bar_text.GetTextProperty()
        txtprop.SetFontSize(14)
        txtprop.SetColor(1.0, 1.0, 1.0)
        self.renderer_slice.AddActor2D(self.scale_bar_text)
        
        self.update_scale_bar()
    
    def update_scale_bar(self):
        """
        Updates the scale bar's endpoints and label based on the current camera view
        in the slice renderer.
        Converts a fixed pixel length (e.g., 100 pixels) to world coordinates.
        """
        width, height = self.render_window.GetSize()
        margin = 20
        pixel_length = 100  # desired length in pixels
        
        # For the left renderer (slice view) which originally occupied half the window:
        left_width = 0.5 * width
        x2 = left_width - margin
        x1 = x2 - pixel_length
        y = margin
        
        self.renderer_slice.SetDisplayPoint(x1, y, 0)
        self.renderer_slice.DisplayToWorld()
        world_point1 = self.renderer_slice.GetWorldPoint()
        if world_point1[3] != 0:
            world_point1 = [world_point1[i] / world_point1[3] for i in range(3)]
        
        self.renderer_slice.SetDisplayPoint(x2, y, 0)
        self.renderer_slice.DisplayToWorld()
        world_point2 = self.renderer_slice.GetWorldPoint()
        if world_point2[3] != 0:
            world_point2 = [world_point2[i] / world_point2[3] for i in range(3)]
        
        dx = world_point2[0] - world_point1[0]
        dy = world_point2[1] - world_point1[1]
        dz = world_point2[2] - world_point1[2]
        world_distance = math.sqrt(dx*dx + dy*dy + dz*dz)
        
        self.scale_bar_text.SetInput(f"{world_distance:.2f} mm")
        text_x = int(x1 + pixel_length/2)
        text_y = y + 10
        self.scale_bar_text.SetDisplayPosition(text_x, text_y)
        
        self.scale_bar_points.SetPoint(0, world_point1[0], world_point1[1], world_point1[2])
        self.scale_bar_points.SetPoint(1, world_point2[0], world_point2[1], world_point2[2])
        self.scale_bar_points.Modified()
        self.scale_bar_polydata.Modified()
        
        self.render_window.Render()
    
    def camera_modified_callback(self, obj, event):
        """Called when the camera changes; update the scale bar accordingly."""
        self.update_scale_bar()
    
    def get_volume_actor(self):
        """
        Creates and returns a vtkVolume actor for volume rendering using the loaded volume.
        """
        vtk_data = self.tomo.create_vtk_volume()
        
        volume_mapper = vtk.vtkSmartVolumeMapper()
        volume_mapper.SetInputData(vtk_data)
        
        volume_property = vtk.vtkVolumeProperty()
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()
        
        volume = vtk.vtkVolume()
        volume.SetMapper(volume_mapper)
        volume.SetProperty(volume_property)
        
        return volume

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FIBTomoVTKApp()
    window.show()
    sys.exit(app.exec())