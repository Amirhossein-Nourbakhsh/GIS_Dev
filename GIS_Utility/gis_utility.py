import sys, os, string, arcpy, logging
from arcpy import env, mapping
import time
from pdf2image import convert_from_path
from PIL import Image

def generate_map_key(input_fc):
    try:
        cur = arcpy.UpdateCursor(input_fc,"" ,"","Dist_cent; MapKeyLoc; MapKeyNo", 'Dist_cent A; Source A')
        row = cur.next()
        # the last value in field A
        last_value = row.getValue('Dist_cent') 
        row.setValue('MapKeyLoc', 1)
        row.setValue('MapKeyNo', 1)

        cur.updateRow(row)
        run = 1 # how many values in this run
        count = 1 # how many runs so far, including the current one
        current_value = 0
        # the for loop should begin from row 2, since
        # cur.next() has already been called once.
        for row in cur:
            current_value = row.getValue('Dist_cent')
            if current_value == last_value:
                run += 1
            else:
                run = 1
                count += 1
            row.setValue('MapKeyLoc', count)
            row.setValue('MapKeyNo', run)
            cur.updateRow(row)
            last_value = current_value
        # release the layer from locks
        del row, cur
        cur = arcpy.UpdateCursor(input_fc, "", "", 'MapKeyLoc; MapKeyNo; MapkeyTot', 'MapKeyLoc D; MapKeyNo D')

        row = cur.next()
        last_value = row.getValue('MapKeyLoc') # the last value in field A
        max= 1
        row.setValue('MapkeyTot', max)
        cur.updateRow(row)
        for row in cur:
            current_value = row.getValue('mapkeyloc')
        if current_value < last_value:
            max= 1
        else:
            max= 0
        row.setValue('MapkeyTot', max)
        cur.updateRow(row)
        last_value = current_value

        # release the layer from locks
        del row, cur
    except:
        # If an error occurred, print the message to the screen
        arcpy.AddMessage(arcpy.GetMessages())


def image_to_tiff_conversion(input_dir): 
    """
    Function converts image to tiff format and returns the number of files converted to tiff. 
    Function can be used to convert files in jpeg, pdf and png format. 

    Process:
    1) Function takes data from input_dir: \\cabcvan1gis005\MISC_DataManagement\Projects\File2TiffConversion\_1_Input
    2) If file is a pdf, it needs to be converted to ppm format prior to converting to tiff. Output files in ppm format are saved
    in intmd_dir: \\cabcvan1gis005\MISC_DataManagement\Projects\File2TiffConversion\_2_Intermediate
    4) Output files converted to tiff are saved in tiff_dir: \\cabcvan1gis005\MISC_DataManagement\Projects\File2TiffConversion\_3_Tiff_converted
    
    When importing the pdf2image library to your machine, install version 1.7.1 for python2 compatibility 
    pip install pdf2image==1.7.1

    """

    total_inputfile_count = 0
    total_files_converted = 0
    input_sub_dirs = os.listdir(input_dir)    

    for item in input_sub_dirs:    
        print "Processing folder ..." + os.path.join(input_dir,item)
        intmd_dir = os.path.join(r"\\cabcvan1gis005\MISC_DataManagement\Projects\File2TiffConversion\_2_Intermediate", item) 
        if not os.path.exists(intmd_dir):
            os.makedirs(intmd_dir)
        tiff_dir = os.path.join(r"\\cabcvan1gis005\MISC_DataManagement\Projects\File2TiffConversion\_3_Tiff_converted",item) 
        if not os.path.exists(tiff_dir):
            os.makedirs(tiff_dir)
        
        if os.path.isfile(os.path.join(input_dir,item)):
            print "WARNING: floating file under " + input_dir
        else:
            for file in os.listdir(os.path.join(input_dir,item)):
                if os.path.isdir(os.path.join(input_dir,item,file)):
                    print "WARNING: nested directory under " + os.path.join(input_dir,item)
                elif file == "Thumbs.db":
                    print "ignore Thumbs.db"
                else:
                    inputfile = os.path.join(input_dir,item,file)
                    if not os.path.exists(inputfile):
                        print "ERROR: The input file does not exist"
                    else:
                        total_inputfile_count = total_inputfile_count + 1
                        
                        #if image is in pdf format - convert pdf to ppm first
                        if inputfile.endswith(".pdf"): 
                            images = convert_from_path(inputfile, output_folder = intmd_dir, fmt="tiff", 
                            output_file = file, poppler_path = r"\\CABCVAN1FPR009\USA_FIPs\_CODES\code\poppler-21.03.0\Library\bin")
                            #convert ppm image to tiff
                            for image in images: 
                                image.save(os.path.join(tiff_dir, file[:-4]) + ".tiff", "TIFF")
                                total_files_converted = total_files_converted + 1
                        #convert remaining images to tiff
                        else:
                            im = Image.open(inputfile) 
                            im.save(os.path.join(tiff_dir, file[:-4]) + ".tiff", "TIFF")
                            total_files_converted = total_files_converted + 1

    print "Total number of input files: " + str(total_inputfile_count)   
    print "Total number of files converted to tiff: " + str(total_files_converted)       
    return total_files_converted


def image_to_8bit(tiff_dir): 
    """
    Function converts tiff images to 8-bit imagery and returns the number of files converted to 8-bit.
    Function takes input data from the tiff_directory (\\cabcvan1gis005\MISC_DataManagement\Projects\File2TiffConversion\_3_Tiff_converted).
    Output files are saved in converted_dir (\\cabcvan1gis005\MISC_DataManagement\Projects\File2TiffConversion\_4_Final_converted_8-bit).

    This function can be used on tiff files. It may be used on other types of image files - require testing. 
    """
    
    total_inputfile_count = 0 
    total_files_8bit = 0
    input_sub_dirs = os.listdir(tiff_dir)    
    
    for item in input_sub_dirs:
        converted_dir = os.path.join(r"\\cabcvan1gis005\MISC_DataManagement\Projects\File2TiffConversion\_4_Final_converted_8-bit",item)
        if not os.path.exists(converted_dir):
            os.makedirs(converted_dir)

        for file in os.listdir(os.path.join(tiff_dir,item)):
            total_inputfile_count = total_inputfile_count + 1
            im = Image.open(os.path.join(tiff_dir, item, file))
            if im.mode == "RGB":        
                #convert RBG images to 8-bit
                im256 = im.quantize(colors=256)
                im256.save(os.path.join(converted_dir,file))
                total_files_8bit = total_files_8bit + 1
            elif im.mode == "1":
                #convert 1-bit images to 8-bit (greyscale)
                im_greyscale = im.convert("L")  
                im_greyscale.save(os.path.join(converted_dir,item))
                total_files_8bit = total_files_8bit + 1 
            else:
                print "Image" + file + "has a different mode, image requires further investigation"
    
    print "Total number of input files: " + str(total_inputfile_count)   
    print "Total number of files converted to 8-bit: " + str(total_files_8bit)   
    
    return total_files_8bit
