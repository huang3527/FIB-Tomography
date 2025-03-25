import streamlit as st
import vtk
from vtkmodules.vtkRenderingCore import vtkRenderWindowInteractor
import numpy as np
import tifffile as tiff
import cv2
import os
import vtkmodules.util.numpy_support as numpy_support

# Function to load TIFF images
def load_images(file_path):
    """Load all TIFF images as a 3D NumPy array."""
    return tiff.TiffFile(r'./image_stack.tif').asarray(key=slice(None))

# Function to create VTK volume
def create_vtk_volume(image_stack):
    """Convert NumPy image stack into VTK image data with proper orientation."""
    depth, height, width = image_stack.shape

    vtk_data = vtk.vtkImageData()
    vtk_data.SetDimensions(width, height, depth)
    vtk_data.SetSpacing(1, 1, 1)
    image_stack = np.transpose(image_stack, (2,1,0))
    vtk_array = numpy_support.numpy_to_vtk(
        num_array=image_stack.ravel(order="F"), 
        deep=True, 
        array_type=vtk.VTK_UNSIGNED_CHAR
    )
    vtk_data.GetPointData().SetScalars(vtk_array)

    return vtk_data

# Function to display 3D visualization in VTK
def show_orthogonal_planes(vtk_data):
    """Display three orthogonal slicing planes in VTK."""
    renderer = vtk.vtkRenderer()
    render_window = vtk.vtkRenderWindow()
    render_window.AddRenderer(renderer)
    interactor = vtkRenderWindowInteractor()
    interactor.SetRenderWindow(render_window)

    # Volume rendering
    volume_mapper = vtk.vtkSmartVolumeMapper()
    volume_mapper.SetInputData(vtk_data)

    volume_property = vtk.vtkVolumeProperty()
    volume_property.ShadeOn()
    volume_property.SetInterpolationTypeToLinear()

    volume = vtk.vtkVolume()
    volume.SetMapper(volume_mapper)
    volume.SetProperty(volume_property)

    renderer.AddVolume(volume)
    renderer.SetBackground(0.2, 0.2, 0.4)  # Set background color

    render_window.Render()
    interactor.Start()

# Function to generate volume rendering in VTK
def generate_volume_rendering(vtk_data):
    """Perform volume rendering and save as an image."""
    volume_mapper = vtk.vtkSmartVolumeMapper()
    volume_mapper.SetInputData(vtk_data)

    volume_property = vtk.vtkVolumeProperty()
    volume_property.ShadeOn()
    volume_property.SetInterpolationTypeToLinear()

    volume = vtk.vtkVolume()
    volume.SetMapper(volume_mapper)
    volume.SetProperty(volume_property)

    renderer = vtk.vtkRenderer()
    render_window = vtk.vtkRenderWindow()
    render_window.SetOffScreenRendering(1)  # Prevent GUI-related errors
    render_window.AddRenderer(renderer)
    renderer.AddVolume(volume)
    renderer.SetBackground(0.2, 0.2, 0.4)

    render_window.Render()
    window_to_image_filter = vtk.vtkWindowToImageFilter()
    window_to_image_filter.SetInput(render_window)
    window_to_image_filter.Update()

    writer = vtk.vtkPNGWriter()
    writer.SetFileName("volume_rendering.png")
    writer.SetInputConnection(window_to_image_filter.GetOutputPort())
    writer.Write()

    return "volume_rendering.png"

# Function to create slice animation
def animate_slices(image_stack, output_file="slices_animation.avi", fps=10):
    """Create an animation from slices of the volume dataset."""
    depth, height, width = image_stack.shape
    max_dim = max(depth, height, width)

    fourcc = cv2.VideoWriter_fourcc(*"XVID")
    video_out = cv2.VideoWriter(output_file, fourcc, fps, (max_dim * 3, max_dim), isColor=False)

    for i in range(depth):
        xy_slice = image_stack[i, :, :]
        yz_slice = image_stack[:, i, :]
        xz_slice = image_stack[:, :, i]

        xy_padded = np.pad(xy_slice, ((0, max_dim - xy_slice.shape[0]), (0, max_dim - xy_slice.shape[1])), mode='constant')
        yz_padded = np.pad(yz_slice, ((0, max_dim - yz_slice.shape[0]), (0, max_dim - yz_slice.shape[1])), mode='constant')
        xz_padded = np.pad(xz_slice, ((0, max_dim - xz_slice.shape[0]), (0, max_dim - xz_slice.shape[1])), mode='constant')

        combined = np.hstack([xy_padded, yz_padded, xz_padded])
        combined = (combined / np.max(combined) * 255).astype(np.uint8)
        combined_colored = cv2.cvtColor(combined, cv2.COLOR_GRAY2BGR)

        video_out.write(combined_colored)

    video_out.release()
    return output_file

# Streamlit UI
st.title("FIB Tomography 3D Visualization")

uploaded_file = st.file_uploader("Upload a TIFF stack", type=["tif", "tiff"])

if uploaded_file:
    with open("temp.tif", "wb") as f:
        f.write(uploaded_file.getbuffer())
    
    st.write("### Loaded TIFF Image Stack")
    image_stack = load_images("temp.tif")
    vtk_data = create_vtk_volume(image_stack)
    
    if st.button("Show 3D Orthogonal Planes Visualization"):
        show_orthogonal_planes(vtk_data)
    
    if st.button("Generate Volume Rendering"):
        volume_image = generate_volume_rendering(vtk_data)
        st.image(volume_image, caption="Volume Rendering", use_column_width=True)
    
    if st.button("Generate Animation from Slices"):
        output_video = animate_slices(image_stack)
        st.video(output_video)
