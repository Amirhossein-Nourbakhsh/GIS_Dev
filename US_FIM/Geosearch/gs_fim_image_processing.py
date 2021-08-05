import sys, os, time, logging
from pdf2image import convert_from_path
from PIL import Image
file_path =os.path.dirname(os.path.abspath(__file__)) 
gis_utility_path = os.path.join(os.path.dirname(os.path.dirname(file_path)),'GIS_Utility')
sys.path.insert(1,gis_utility_path)
import gis_utility
 

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.FileHandler(r"\\cabcvan1gis005\MISC_DataManagement\Projects\File2TiffConversion\pdftotiff_timelog.txt")
handler.setLevel(logging.INFO)
logger.addHandler(handler)

if __name__ == "__main__":
    
    input_dir = r"\\cabcvan1gis005\MISC_DataManagement\Projects\File2TiffConversion\_1_Input" #input folder for tiff conversion
    tiff_dir = r"\\cabcvan1gis005\MISC_DataManagement\Projects\File2TiffConversion\_3_Tiff_converted" #input folder for 8-bit conversion

    #Convert file to tiff    
    starttime = time.time()
    logger.info("Tiff conversion started at "+ time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

    tiff_img = gis_utility.image_to_tiff_conversion(input_dir)

    endtime = time.time()
    logger.info("Finished at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    logger.info("Total number files converted to tiff: " + str(tiff_img))
    logger.info("Average tiff conversion speed (#files /s): " + str(tiff_img/(endtime-starttime)) + "\n")

    ## Convert file to 8-bit    
    starttime = time.time()
    logger.info("8-bit conversion started at "+ time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))

    tiff_8_bit = gis_utility.image_to_8bit(tiff_dir)

    endtime = time.time()
    logger.info("Finished at " + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
    logger.info("Total number files converted to 8-bit: " + str(tiff_8_bit))
    logger.info("Average bit conversion speed (#files /s): " + str(tiff_8_bit/(endtime-starttime)) + "\n")

    print "DONE! Please review files in: " + r"\\cabcvan1gis005\MISC_DataManagement\Projects\File2TiffConversion\_4_Final_converted_8-bit"
   
logger.removeHandler(handler)
handler.flush()
handler.close()



