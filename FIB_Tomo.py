import vtk
import numpy as np
import tifffile as tiff
import cv2
import os
import vtkmodules.util.numpy_support as numpy_support
from vtkmodules.vtkRenderingCore import vtkRenderWindowInteractor

class FIBTomo:
    
    def __init__(self, dims=(100, 100, 100)):
        """
        Initialize a 3D volume.
        If a volume is not loaded from a TIFF stack, synthetic data with a gradient pattern is generated.
        dims: tuple (depth, height, width)
        """
        self.dims = dims
        self.volume = None
        self.loaded = False
        # Default slice indices for each axis (centered)
        self.x_offset = dims[2] // 2
        self.y_offset = dims[1] // 2
        self.z_offset = dims[0] // 2
    
    def update_slice(self, x, y, z):
        """Update the slice offsets.
        This method sets the x_offset, y_offset, and z_offset values.
        """
        self.x_offset = x
        self.y_offset = y
        self.z_offset = z
    
    def load_image(self, filename=None):
        """
        Load a TIFF stack as a 3D NumPy array from the specified file path.
        If no filename is provided, synthetic volume data is generated.
        """
        if filename is None:
            # Generate synthetic volume data with a horizontal gradient.
            self.volume = np.zeros(self.dims, dtype=np.uint8)
            for z in range(self.dims[0]):
                for y in range(self.dims[1]):
                    self.volume[z, y, :] = np.linspace(0, 255, self.dims[2], dtype=np.uint8)
        else:
            # Load the TIFF stack from the given filename.
            self.volume = tiff.TiffFile(filename).asarray(key=slice(None))
        self.loaded = True
        # Reset offsets to the center of the volume.
        self.x_offset = self.dims[2] // 2
        self.y_offset = self.dims[1] // 2
        self.z_offset = self.dims[0] // 2
        return self.volume
        
    def get_vtk_image(self):
        """
        Convert a 2D axial slice (using the current z_offset) of the 3D volume 
        into a vtkImageData object.
        """
        if not self.loaded or self.volume is None:
            raise ValueError("No volume loaded. Call load_image() first.")
        # Clamp z_offset to a valid index.
        z_index = int(np.clip(self.z_offset, 0, self.volume.shape[0] - 1))
        slice_2d = self.volume[z_index, :, :]  # axial slice
        height, width = slice_2d.shape

        # Convert the 2D NumPy array to raw bytes.
        data_string = slice_2d.tobytes()

        # Use vtkImageImport to convert raw bytes into vtkImageData.
        image_import = vtk.vtkImageImport()
        image_import.CopyImportVoidPointer(data_string, len(data_string))
        image_import.SetDataScalarTypeToUnsignedChar()
        image_import.SetNumberOfScalarComponents(1)
        image_import.SetWholeExtent(0, width - 1, 0, height - 1, 0, 0)
        image_import.SetDataExtentToWholeExtent()
        image_import.Update()
        return image_import.GetOutput()
    
    def create_vtk_volume(self, image_stack=None):
        """
        Convert a NumPy image stack into vtkImageData with proper orientation.
        If image_stack is None, the loaded volume is used.
        """
        if image_stack is None:
            if not self.loaded or self.volume is None:
                raise ValueError("No volume loaded. Call load_image() first.")
            image_stack = self.volume
        depth, height, width = image_stack.shape

        vtk_data = vtk.vtkImageData()
        vtk_data.SetDimensions(width, height, depth)
        vtk_data.SetSpacing(1, 1, 1)
        # Transpose the array to match VTK's (x, y, z) order.
        transposed = np.transpose(image_stack, (2, 1, 0))
        vtk_array = numpy_support.numpy_to_vtk(
            num_array=transposed.ravel(order="F"), 
            deep=True, 
            array_type=vtk.VTK_UNSIGNED_CHAR
        )
        vtk_data.GetPointData().SetScalars(vtk_array)

        return vtk_data

    def show_orthogonal_planes(self, vtk_data=None):
        """
        Display three orthogonal slicing planes in VTK.
        Axial (z), coronal (y), and sagittal (x) slices are shown side-by-side.
        If vtk_data is not provided, the volume is used.
        """
        if vtk_data is None:
            vtk_data = self.create_vtk_volume()
        
        renderer = vtk.vtkRenderer()
        render_window = vtk.vtkRenderWindow()
        render_window.AddRenderer(renderer)
        interactor = vtkRenderWindowInteractor()
        interactor.SetRenderWindow(render_window)

        # Axial slice (z-axis)
        axial_image = self.get_vtk_image()
        axial_actor = vtk.vtkImageActor()
        axial_actor.GetMapper().SetInputData(axial_image)
        axial_actor.SetPosition(0, 0, 0)
        
        # Coronal slice (y-axis)
        y_index = int(np.clip(self.y_offset, 0, self.volume.shape[1] - 1))
        coronal_slice = self.volume[:, y_index, :]
        depth, width = coronal_slice.shape
        data_string = coronal_slice.tobytes()
        image_import = vtk.vtkImageImport()
        image_import.CopyImportVoidPointer(data_string, len(data_string))
        image_import.SetDataScalarTypeToUnsignedChar()
        image_import.SetNumberOfScalarComponents(1)
        image_import.SetWholeExtent(0, width - 1, 0, depth - 1, 0, 0)
        image_import.SetDataExtentToWholeExtent()
        image_import.Update()
        coronal_actor = vtk.vtkImageActor()
        coronal_actor.GetMapper().SetInputData(image_import.GetOutput())
        coronal_actor.SetPosition(width + 10, 0, 0)  # Offset for display
        
        # Sagittal slice (x-axis)
        x_index = int(np.clip(self.x_offset, 0, self.volume.shape[2] - 1))
        sagittal_slice = self.volume[:, :, x_index]
        depth, height = sagittal_slice.shape
        data_string = sagittal_slice.tobytes()
        image_import = vtk.vtkImageImport()
        image_import.CopyImportVoidPointer(data_string, len(data_string))
        image_import.SetDataScalarTypeToUnsignedChar()
        image_import.SetNumberOfScalarComponents(1)
        image_import.SetWholeExtent(0, height - 1, 0, depth - 1, 0, 0)
        image_import.SetDataExtentToWholeExtent()
        image_import.Update()
        sagittal_actor = vtk.vtkImageActor()
        sagittal_actor.GetMapper().SetInputData(image_import.GetOutput())
        sagittal_actor.SetPosition(width + 10, depth + 10, 0)  # Offset for display
        
        renderer.AddActor(axial_actor)
        renderer.AddActor(coronal_actor)
        renderer.AddActor(sagittal_actor)
        renderer.SetBackground(0.2, 0.2, 0.4)

        render_window.Render()
        interactor.Start()

    def generate_volume_rendering(self, vtk_data=None):
        """
        Perform volume rendering of the volume and display it in an interactive render window.
        If vtk_data is not provided, the loaded volume is used.
        """
        if vtk_data is None:
            vtk_data = self.create_vtk_volume()
            
        volume_mapper = vtk.vtkSmartVolumeMapper()
        volume_mapper.SetInputData(vtk_data)

        volume_color = vtk.vtkColorTransferFunction()
        volume_color.AddRGBPoint(0, 0.0, 0.0, 0.0)
        volume_color.AddRGBPoint(255, 1.0, 1.0, 1.0)

        volume_scalar_opacity = vtk.vtkPiecewiseFunction()
        volume_scalar_opacity.AddPoint(0, 0.0)
        volume_scalar_opacity.AddPoint(255, 1.0)
        
        volume_property = vtk.vtkVolumeProperty()
        volume_property.SetColor(volume_color)
        volume_property.SetScalarOpacity(volume_scalar_opacity)
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()
        
        volume = vtk.vtkVolume()
        volume.SetMapper(volume_mapper)
        volume.SetProperty(volume_property)
        
        renderer = vtk.vtkRenderer()
        render_window = vtk.vtkRenderWindow()
        render_window.AddRenderer(renderer)
        
        interactor = vtk.vtkRenderWindowInteractor()
        interactor.SetRenderWindow(render_window)
        
        renderer.AddVolume(volume)
        renderer.SetBackground(0.2, 0.2, 0.4)
        
        render_window.SetSize(800, 600)
        render_window.Render()
        interactor.Initialize()
        interactor.Start()

    def animate_slices(self, output_file="slices_animation.avi", fps=10):
        """
        Create an animation from slices of the volume dataset.
        The animation displays combined views of axial, coronal, and sagittal slices.
        """
        if not self.loaded or self.volume is None:
            raise ValueError("No volume loaded. Call load_image() first.")
        depth, height, width = self.volume.shape
        max_dim = max(depth, height, width)

        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        video_out = cv2.VideoWriter(output_file, fourcc, fps, (max_dim * 3, max_dim), isColor=False)

        for i in range(depth):
            # Axial slice (xy-plane)
            xy_slice = self.volume[i, :, :]
            # Coronal slice (yz-plane)
            yz_slice = self.volume[:, i, :]
            # Sagittal slice (xz-plane)
            xz_slice = self.volume[:, :, i]

            xy_padded = np.pad(xy_slice, ((0, max_dim - xy_slice.shape[0]), (0, max_dim - xy_slice.shape[1])), mode='constant')
            yz_padded = np.pad(yz_slice, ((0, max_dim - yz_slice.shape[0]), (0, max_dim - yz_slice.shape[1])), mode='constant')
            xz_padded = np.pad(xz_slice, ((0, max_dim - xz_slice.shape[0]), (0, max_dim - xz_slice.shape[1])), mode='constant')

            combined = np.hstack([xy_padded, yz_padded, xz_padded])
            # Normalize to full 8-bit range and convert to color for video writing.
            combined = (combined / np.max(combined) * 255).astype(np.uint8)
            combined_colored = cv2.cvtColor(combined, cv2.COLOR_GRAY2BGR)

            video_out.write(combined_colored)

        video_out.release()
        return output_file

# For standalone testing:
if __name__ == "__main__":
    tomo = FIBTomo()
    # Test loading a synthetic volume or provide a TIFF file path, e.g.:
    # tomo.load_image("path/to/tiff_stack.tif")
    tomo.load_image(r'./image_stack.tif')
    vtk_img = tomo.get_vtk_image()
    vtk_vol = tomo.create_vtk_volume()
    tomo.generate_volume_rendering()
    # tomo.show_orthogonal_planes()
    print("vtkImageData dimensions:", vtk_img.GetDimensions())