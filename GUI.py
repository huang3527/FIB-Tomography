import sys
import math
import vtk
from PySide6.QtWidgets import (QApplication, QWidget, QHBoxLayout, QVBoxLayout, QLabel, 
                               QComboBox, QSlider, QSplitter)
from PySide6.QtCore import Qt
from vtkmodules.qt.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor
from FIB_Tomo import FIBTomo

class FIBTomoVTKApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # Instantiate FIBTomo and load the TIFF stack.
        self.tomo = FIBTomo()
        self.tomo.load_image(r'./image_stack.tif')
        # Set initial offsets to something other than the center:
        
        # Set initial opacities.
        self.slice_opacity = 1.0
        self.volume_opacity = 1.0

        # Create the QVTKRenderWindowInteractor widget.
        self.vtkWidget = QVTKRenderWindowInteractor(self)
        self.render_window = self.vtkWidget.GetRenderWindow()
        
        # We'll use one renderer and swap its contents.
        self.renderer = vtk.vtkRenderer()
        self.renderer.SetBackground(0.2, 0.2, 0.4)
        self.render_window.AddRenderer(self.renderer)
        
        # Create the left control panel.
        self.control_panel = QWidget()
        control_layout = QVBoxLayout(self.control_panel)
        
        # 1. View mode selection box.
        self.view_combo = QComboBox()
        self.view_combo.addItems(["Volume Rendering", "Slice View"])
        self.view_combo.setCurrentText("Volume Rendering")
        self.view_combo.currentTextChanged.connect(self.change_view_mode)
        control_layout.addWidget(QLabel("Select view mode:"))
        control_layout.addWidget(self.view_combo)
        
        # 2. X, Y, Z offset sliders.
        self.x_slider = QSlider(Qt.Horizontal)
        self.y_slider = QSlider(Qt.Horizontal)
        self.z_slider = QSlider(Qt.Horizontal)
        for slider in [self.x_slider, self.y_slider, self.z_slider]:
            slider.valueChanged.connect(self.update_slice_offset)
        control_layout.addWidget(QLabel("X Offset:"))
        control_layout.addWidget(self.x_slider)
        control_layout.addWidget(QLabel("Y Offset:"))
        control_layout.addWidget(self.y_slider)
        control_layout.addWidget(QLabel("Z Offset:"))
        control_layout.addWidget(self.z_slider)
        
        # 3. Opacity slider for volume rendering.
        self.volume_opacity_slider = QSlider(Qt.Horizontal)
        self.volume_opacity_slider.setRange(0, 100)
        self.volume_opacity_slider.setValue(100)
        self.volume_opacity_slider.valueChanged.connect(self.update_volume_opacity)
        control_layout.addWidget(QLabel("Volume Opacity:"))
        control_layout.addWidget(self.volume_opacity_slider)
        
        # 4. Opacity slider for slice view.
        self.slice_opacity_slider = QSlider(Qt.Horizontal)
        self.slice_opacity_slider.setRange(0, 100)
        self.slice_opacity_slider.setValue(100)
        self.slice_opacity_slider.valueChanged.connect(self.update_slice_opacity)
        control_layout.addWidget(QLabel("Slice Opacity:"))
        control_layout.addWidget(self.slice_opacity_slider)
        
        control_layout.addStretch()
        
        # Create a splitter: left (controls) and right (VTK widget) with ratio 2:3.
        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self.control_panel)
        splitter.addWidget(self.vtkWidget)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 3)
        
        main_layout = QHBoxLayout(self)
        main_layout.addWidget(splitter)
        self.setLayout(main_layout)
        
        # Initialize and start the VTK interactor.
        self.vtkWidget.Initialize()
        self.vtkWidget.Start()
        
        # Set initial view mode.
        self.change_view_mode(self.view_combo.currentText())
    
    def change_view_mode(self, mode):
        """
        Update the renderer based on the selected view mode.
        Also adjust slider ranges and initial values based on the volume dimensions.
        
        For "Volume Rendering" mode:
          - Set slider ranges to the full object dimensions.
          - Set slider values to maximum (so clipping planes are at the boundaries).
          
        For "Slice View" mode:
          - Set slider ranges to the full object dimensions.
          - Set slider values to the center (for an isometric triplanar view).
        """
        # Get the volume dimensions.
        # FIBTomo volume shape is assumed to be (depth, height, width)
        depth, height, width = self.tomo.volume.shape
        
        if mode == "Volume Rendering":
            # Set slider ranges and set initial values to the maximum boundary.
            self.x_slider.setRange(0, width)
            self.y_slider.setRange(0, height)
            self.z_slider.setRange(0, depth)
            self.x_slider.setValue(0)
            self.y_slider.setValue(0)
            self.z_slider.setValue(0)
            self.tomo.update_slice(width, height, depth)
            # Remove any previous actors.
            self.renderer.RemoveAllViewProps()
            self.volume_actor = self.get_volume_actor()
            self.renderer.AddVolume(self.volume_actor)
        elif mode == "Slice View":
            # Set slider ranges and set initial values to the center.
            self.x_slider.setRange(0, width)
            self.y_slider.setRange(0, height)
            self.z_slider.setRange(0, depth)
            center_x = width // 2
            center_y = height // 2
            center_z = depth // 2
            self.x_slider.setValue(center_x)
            self.y_slider.setValue(center_y)
            self.z_slider.setValue(center_z)
            self.tomo.update_slice(center_x, center_y, center_z)
            self.renderer.RemoveAllViewProps()
            self.slice_actors = self.create_orthogonal_slice_actors()
            for actor in self.slice_actors:
                self.renderer.AddActor(actor)
        self.renderer.ResetCamera()
        self.render_window.Render()
    
    def update_slice_offset(self):
        """
        Update the slice offsets from the slider values.
        In "Volume Rendering" mode, update the clipping plane origins.
        In "Slice View" mode, recreate the orthogonal slice actors.
        """
        x = self.x_slider.value()
        y = self.y_slider.value()
        z = self.z_slider.value()
        self.tomo.update_slice(x, y, z)
        mode = self.view_combo.currentText()
        if mode == "Slice View":
            self.renderer.RemoveAllViewProps()
            self.slice_actors = self.create_orthogonal_slice_actors()
            for actor in self.slice_actors:
                self.renderer.AddActor(actor)
        elif mode == "Volume Rendering":
            if hasattr(self, "plane_x"):
                self.plane_x.SetOrigin(x, 0, 0)
            if hasattr(self, "plane_y"):
                self.plane_y.SetOrigin(0, y, 0)
            if hasattr(self, "plane_z"):
                self.plane_z.SetOrigin(0, 0, z)
        self.renderer.ResetCamera()
        self.render_window.Render()
    
    def update_volume_opacity(self, value):
        """Update the volume rendering opacity via the scalar opacity transfer function."""
        self.volume_opacity = value / 100.0
        if self.view_combo.currentText() == "Volume Rendering":
            opacity_transfer = vtk.vtkPiecewiseFunction()
            opacity_transfer.AddPoint(0, 0.0)
            opacity_transfer.AddPoint(255, self.volume_opacity)
            self.volume_actor.GetProperty().SetScalarOpacity(opacity_transfer)
            self.render_window.Render()
    
    def update_slice_opacity(self, value):
        """Update the opacity for each slice actor."""
        self.slice_opacity = value / 100.0
        if self.view_combo.currentText() == "Slice View":
            for actor in self.slice_actors:
                actor.GetProperty().SetOpacity(self.slice_opacity)
            self.render_window.Render()
    
    def get_volume_actor(self):
        """
        Create and return a vtkVolume actor with clipping planes based on offset sliders.
        """
        vtk_data = self.tomo.create_vtk_volume()
        self.volume_mapper = vtk.vtkSmartVolumeMapper()
        self.volume_mapper.SetInputData(vtk_data)
        
        # Create clipping planes.
        self.clip_planes = vtk.vtkPlaneCollection()
        self.plane_x = vtk.vtkPlane()
        self.plane_x.SetNormal(1, 0, 0)
        self.plane_x.SetOrigin(self.tomo.x_offset, 0, 0)
        
        self.plane_y = vtk.vtkPlane()
        self.plane_y.SetNormal(0, 1, 0)
        self.plane_y.SetOrigin(0, self.tomo.y_offset, 0)
        
        self.plane_z = vtk.vtkPlane()
        self.plane_z.SetNormal(0, 0, 1)
        self.plane_z.SetOrigin(0, 0, self.tomo.z_offset)
        
        self.clip_planes.AddItem(self.plane_x)
        self.clip_planes.AddItem(self.plane_y)
        self.clip_planes.AddItem(self.plane_z)
        self.volume_mapper.SetClippingPlanes(self.clip_planes)
        
        volume_property = vtk.vtkVolumeProperty()
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()
        volume_property.SetScalarOpacityUnitDistance(1)
        opacity_transfer = vtk.vtkPiecewiseFunction()
        opacity_transfer.AddPoint(0, 0.0)
        opacity_transfer.AddPoint(255, self.volume_opacity)
        volume_property.SetScalarOpacity(opacity_transfer)
        
        volume = vtk.vtkVolume()
        volume.SetMapper(self.volume_mapper)
        volume.SetProperty(volume_property)
        return volume
    
    def create_orthogonal_slice_actors(self):
        """
        Create and return three vtkImageActor objects for axial, coronal, and sagittal slices,
        arranged so that their centers coincide (i.e. an isometric triplanar view centered on the volume).
        """
        # Axial slice (XY plane) from self.tomo.get_vtk_image()
        axial_image = self.tomo.get_vtk_image()
        dims = axial_image.GetDimensions()  # (width, height, 1)
        width, height = dims[0], dims[1]
        axial_actor = vtk.vtkImageActor()
        axial_actor.GetMapper().SetInputData(axial_image)
        axial_actor.GetProperty().SetOpacity(self.slice_opacity)
        # Move the axial actor so that its center is at (0,0,0)
        axial_actor.SetPosition(-width / 2.0, -height / 2.0, 0)
        
        # Coronal slice (YZ plane): slice from volume at y offset.
        y_index = int(self.tomo.y_offset)
        coronal_slice = self.tomo.volume[:, y_index, :]  # shape: (depth, width)
        coronal_image = self.convert_numpy_to_vtk_image(coronal_slice)
        dims_corr = coronal_image.GetDimensions()  # (width_corr, depth_corr, 1)
        width_corr, depth_corr = dims_corr[0], dims_corr[1]
        coronal_actor = vtk.vtkImageActor()
        coronal_actor.GetMapper().SetInputData(coronal_image)
        coronal_actor.GetProperty().SetOpacity(self.slice_opacity)
        # Rotate so that the slice lies in the correct plane.
        coronal_actor.RotateX(90)
        # After rotation, center the actor.
        coronal_actor.SetPosition(-width_corr / 2.0, -depth_corr / 2.0, 0)
        
        # Sagittal slice (XZ plane): slice from volume at x offset.
        x_index = int(self.tomo.x_offset)
        sagittal_slice = self.tomo.volume[:, :, x_index]  # shape: (depth, height)
        sagittal_image = self.convert_numpy_to_vtk_image(sagittal_slice)
        dims_sag = sagittal_image.GetDimensions()  # (width_sag, height_sag, 1)
        # For sagittal, the array shape is (depth, height) so interpret width_sag as height and height_sag as depth.
        height_sag, depth_sag = dims_sag[0], dims_sag[1]
        sagittal_actor = vtk.vtkImageActor()
        sagittal_actor.GetMapper().SetInputData(sagittal_image)
        sagittal_actor.GetProperty().SetOpacity(self.slice_opacity)
        sagittal_actor.RotateY(90)
        sagittal_actor.SetPosition(-height_sag / 2.0, -depth_sag / 2.0, 0)
        
        return [axial_actor, coronal_actor, sagittal_actor]
    
    def convert_numpy_to_vtk_image(self, np_array):
        """
        Convert a 2D NumPy array to a vtkImageData object.
        """
        height, width = np_array.shape
        data_string = np_array.tobytes()
        image_import = vtk.vtkImageImport()
        image_import.CopyImportVoidPointer(data_string, len(data_string))
        image_import.SetDataScalarTypeToUnsignedChar()
        image_import.SetNumberOfScalarComponents(1)
        image_import.SetWholeExtent(0, width - 1, 0, height - 1, 0, 0)
        image_import.SetDataExtentToWholeExtent()
        image_import.Update()
        return image_import.GetOutput()
    
    def update_scale_bar(self):
        width, height = self.render_window.GetSize()
        margin = 20
        pixel_length = 100
        left_width = 0.5 * width
        x2 = left_width - margin
        x1 = x2 - pixel_length
        y = margin
        
        self.renderer.SetDisplayPoint(x1, y, 0)
        self.renderer.DisplayToWorld()
        world_point1 = self.renderer.GetWorldPoint()
        if world_point1[3] != 0:
            world_point1 = [world_point1[i] / world_point1[3] for i in range(3)]
        
        self.renderer.SetDisplayPoint(x2, y, 0)
        self.renderer.DisplayToWorld()
        world_point2 = self.renderer.GetWorldPoint()
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
    
    def add_scale_bar(self):
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
        self.renderer.AddActor2D(self.scale_bar_actor)
        
        self.scale_bar_text = vtk.vtkTextActor()
        txtprop = self.scale_bar_text.GetTextProperty()
        txtprop.SetFontSize(14)
        txtprop.SetColor(1.0, 1.0, 1.0)
        self.renderer.AddActor2D(self.scale_bar_text)
        
        self.update_scale_bar()
    
if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = FIBTomoVTKApp()
    window.show()
    sys.exit(app.exec())