from PIL import Image, ImageSequence
import os
import numpy as np
import matplotlib.pyplot as plt
import cv2 
import vtk
import numpy as np
import tifffile as tiff
import os
import vtkmodules.util.numpy_support as numpy_support

class VTK3DReconstruction:
    def __init__(self):
        """Initialize VTK-based volume cropping."""
        self.image_stack = self.load_images()
        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk.vtkRenderWindow()
        self.interactor = vtk.vtkRenderWindowInteractor()
        self.volume_actor = None  # Store volume rendering actor
        self.vtk_data = None
        self.active_slice_axis = None  # Track active slice direction
        self.planes = {}  # Store slicing planes
        self.plane_actors = {}  # Store plane actors for visualization

    def load_images(self):
        """Load all TIFF images as a 3D numpy array."""
        image_stack = tiff.TiffFile(r'./image_stack.tif').asarray(key=slice(None))
        return image_stack

    def create_vtk_volume(self):
        """Convert NumPy image stack into VTK image data with proper orientation."""
        depth, height, width = self.image_stack.shape

        vtk_data = vtk.vtkImageData()
        vtk_data.SetDimensions(width, height, depth)
        vtk_data.SetSpacing(1, 1, 1)
        self.image_stack = np.transpose(self.image_stack, (2,1,0))
        vtk_array = numpy_support.numpy_to_vtk(num_array=self.image_stack.ravel(order="F"), deep=True, array_type=vtk.VTK_UNSIGNED_CHAR)

        vtk_data.GetPointData().SetScalars(vtk_array)
        return vtk_data

    def add_slicing_planes(self):
        """Add multiple slicing planes (X, Y, Z) for selective visualization."""
        colors = [(1, 0, 0), (0, 1, 0), (0, 0, 1)]  # Red, Green, Blue
        axes = ["X", "Y", "Z"]
        
        for i, axis in enumerate(axes):
            plane = vtk.vtkPlane()
            plane.SetOrigin(self.vtk_data.GetCenter())  # Start at center
            self.planes[axis] = plane

            cutter = vtk.vtkCutter()
            cutter.SetInputData(self.vtk_data)
            cutter.SetCutFunction(plane)
            cutter.Update()

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(cutter.GetOutputPort())

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(colors[i])
            actor.GetProperty().SetOpacity(0.8)  # Semi-transparent

            self.renderer.AddActor(actor)
            self.plane_actors[axis] = actor  # Store for updating

    def apply_volume_rendering(self):
        """Apply volume rendering to the dataset."""
        print("Applying volume rendering...")

        # Volume Mapper
        volume_mapper = vtk.vtkSmartVolumeMapper()
        volume_mapper.SetInputData(self.vtk_data)

        # Opacity Mapping
        opacity_function = vtk.vtkPiecewiseFunction()
        opacity_function.AddPoint(0, 0.0)
        opacity_function.AddPoint(127, 0.1)
        opacity_function.AddPoint(255, 1.0)

        # Color Mapping
        color_function = vtk.vtkColorTransferFunction()
        color_function.AddRGBPoint(0, 0.0, 0.0, 0.0)
        color_function.AddRGBPoint(127, 1.0, 0.5, 0.3)
        color_function.AddRGBPoint(255, 1.0, 1.0, 1.0)

        # Volume Properties
        volume_property = vtk.vtkVolumeProperty()
        volume_property.SetColor(color_function)
        volume_property.SetScalarOpacity(opacity_function)
        volume_property.ShadeOn()
        volume_property.SetInterpolationTypeToLinear()

        # Volume Actor
        self.volume_actor = vtk.vtkVolume()
        self.volume_actor.SetMapper(volume_mapper)
        self.volume_actor.SetProperty(volume_property)

        self.renderer.AddVolume(self.volume_actor)

    def navigate_to_slice(self, axis, slice_position):
        """Move to a specific slice and remove volume rendering in that direction."""
        # Remove volume rendering in the selected axis
        if self.volume_actor in self.renderer.GetVolumes():
            self.renderer.RemoveVolume(self.volume_actor)

        # Hide other slice planes except the selected one
        for plane_axis, actor in self.plane_actors.items():
            if plane_axis == axis:
                actor.VisibilityOn()
            else:
                actor.VisibilityOff()

        # Move the selected slicing plane
        if axis in self.planes:
            self.planes[axis].SetOrigin(slice_position)

        self.render_window.Render()

        # Re-enable volume rendering in the other directions
        self.renderer.AddVolume(self.volume_actor)
        self.render_window.Render()

    def keyboard_callback(self, obj, event):
        """Keyboard interaction for selecting slice planes."""
        key = obj.GetKeySym()
        movement = 5  # Step size for slice movement
        center = list(self.vtk_data.GetCenter())

        if key == "x":
            self.active_slice_axis = "X"
            self.navigate_to_slice("X", (center[0] + movement, center[1], center[2]))
        elif key == "y":
            self.active_slice_axis = "Y"
            self.navigate_to_slice("Y", (center[0], center[1] + movement, center[2]))
        elif key == "z":
            self.active_slice_axis = "Z"
            self.navigate_to_slice("Z", (center[0], center[1], center[2] + movement))

    def display_slices(self, slice_index=None):
        """Display slices along XY, YZ, and XZ planes."""
        if slice_index is None:
            slice_index = self.image_stack.shape[0] // 2  # Default to middle slice

        xy_slice = self.image_stack[slice_index, :, :]
        yz_slice = self.image_stack[:, slice_index, :]
        xz_slice = self.image_stack[:, :, slice_index]

        fig, axes = plt.subplots(1, 3, figsize=(12, 4))

        axes[0].imshow(xy_slice, cmap="gray")
        axes[0].set_title(f"XY Plane - Slice {slice_index}")

        axes[1].imshow(yz_slice, cmap="gray")
        axes[1].set_title(f"YZ Plane - Slice {slice_index}")

        axes[2].imshow(xz_slice, cmap="gray")
        axes[2].set_title(f"XZ Plane - Slice {slice_index}")

        for ax in axes:
            ax.axis("off")

        plt.show()

    def show_orthogonal_planes(self):
        """Display three orthogonal slicing planes in VTK for volume visualization."""
        self.vtk_data = self.create_vtk_volume()

        self.renderer = vtk.vtkRenderer()
        self.render_window = vtk.vtkRenderWindow()
        self.render_window.AddRenderer(self.renderer)
        self.render_window.SetSize(1600, 1200)
        self.interactor = vtk.vtkRenderWindowInteractor()
        self.interactor.SetRenderWindow(self.render_window)

        # Define three slicing planes (XY, YZ, XZ)
        planes = []
        colors = [(1, 1, 1), (1, 0, 0), (0, 1, 0)]  # White, Red, Green for visibility

        for i, normal in enumerate([(1, 0, 0), (0, 1, 0), (0, 0, 1)]):
            plane = vtk.vtkPlane()
            plane.SetOrigin(self.vtk_data.GetCenter())  # Center at volume center
            plane.SetNormal(normal)

            cutter = vtk.vtkCutter()
            cutter.SetCutFunction(plane)
            cutter.SetInputData(self.vtk_data)
            cutter.Update()

            mapper = vtk.vtkPolyDataMapper()
            mapper.SetInputConnection(cutter.GetOutputPort())

            actor = vtk.vtkActor()
            actor.SetMapper(mapper)
            actor.GetProperty().SetColor(colors[i])
            actor.GetProperty().SetOpacity(0.5)  # Semi-transparent slices
            planes.append(actor)
            self.renderer.AddActor(actor)

    def animate_slices(self, output_file=r"./slices_animation.avi", fps=10):
        """Create an animation from slices of the volume dataset in XY, YZ, and XZ planes."""
        print(f"Creating animation: {output_file}")

        depth, height, width = self.image_stack.shape
        max_dim = max(depth, height, width)
        # Define video writer
        fourcc = cv2.VideoWriter_fourcc(*"XVID")
        video_out = cv2.VideoWriter(output_file, fourcc, fps, (width * 3, height), isColor=False)

        for i in range(depth):  # Loop over all slices
            xy_slice = self.image_stack[i, :, :]
            yz_slice = self.image_stack[:, i, :]
            xz_slice = self.image_stack[:, :, i]

            xy_padded = np.pad(xy_slice, ((0, max_dim - xy_slice.shape[0]), (0, max_dim - xy_slice.shape[1])), mode='constant')
            yz_padded = np.pad(yz_slice, ((0, max_dim - yz_slice.shape[0]), (0, max_dim - yz_slice.shape[1])), mode='constant')
            xz_padded = np.pad(xz_slice, ((0, max_dim - xz_slice.shape[0]), (0, max_dim - xz_slice.shape[1])), mode='constant')

            # Stack the three slices horizontally
            combined = np.hstack([xy_padded, yz_padded, xz_padded])
            combined = (combined / np.max(combined) * 255).astype(np.uint8)  # Normalize to 8-bit
            combined_colored = cv2.cvtColor(combined, cv2.COLOR_GRAY2BGR)  # Convert to BGR

            video_out.write(combined_colored)  # Write frame

        video_out.release()
        print(f"Animation saved: {output_file}")

    def visualize_3d_model(self):
        """Visualize the 3D reconstructed model with selective slice planes and volume rendering."""
        self.render_window.SetSize(1600, 1200)
        self.render_window.AddRenderer(self.renderer)
        self.interactor.SetRenderWindow(self.render_window)
        

        self.vtk_data = self.create_vtk_volume()

        # Add Slicing Planes
        self.add_slicing_planes()

        # Apply Volume Rendering
        # self.apply_volume_rendering()

        self.show_orthogonal_planes()

        # Keyboard Interaction
        self.interactor.AddObserver("KeyPressEvent", self.keyboard_callback)

        print("Displaying 3D model with selective slice planes and volume rendering...")
        self.renderer.ResetCamera()
        self.renderer.ResetCameraClippingRange()
        self.render_window.Render()
        self.interactor.Start()

    def run_pipeline(self):
        """Run the full VTK pipeline for 3D reconstruction, slicing, and volume rendering."""
        self.visualize_3d_model()
        self.animate_slices(output_file=r"./output.avi", fps=10)  # Create slice animation
if __name__ == "__main__":
    processor = VTK3DReconstruction()
    processor.run_pipeline()