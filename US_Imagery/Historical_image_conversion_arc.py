## Loop through each image, apply spatial reference & produce .xml that ArcGiS can read. Temporarily save output to new location
import arcpy, os
##source files
def image_properties(image_path):
    sr = arcpy.SpatialReference(4326)
    arcpy.DefineProjection_management(image_path,sr)
    arcpy.Copy_management(image_path, os.path.join(arc_image_output, os.path.basename(image_path)))
    return 'success'

orig_image_file = r'C:\Users\JLoucks\Desktop\imagetest_US'
arc_image_output = r'C:\Users\JLoucks\Desktop\output_test'
file_extensions = ('.tif','.tiff','.jpg','.jpeg','.png','.sid')
for aerial_image in os.listdir(orig_image_file):
    if aerial_image.endswith(file_extensions):
        image_properties(aerial_image)
    else:
        print aerial_image

        