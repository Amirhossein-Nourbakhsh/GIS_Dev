#-------------------------------------------------------------------------------
# Name:        HTMC_US_single
# Purpose:     Converts USGS current Topographic maps from geoPDF to geoTIF using GDAL. 
#              Only for converting individual pdfs instead of batch or running entire script, or testing and debugging purpose.
#-------------------------------------------------------------------------------

from osgeo import osr, gdal, ogr
import multiprocessing as mp
import PyPDF2
import xml.etree.ElementTree as ET
import subprocess as sub
import os
import re
import time

class TOPO_Process():
    def cropt(self, csvtemppath, gdalpath, tifpath_t, pdfpath):
        # CROP IMAGE_t
        command1 = (fr'{gdalpath}\gdalwarp.exe "{pdfpath}" "{tifpath_t}" ' +
                    f'-cutline "{csvtemppath}" ' +
                    '-crop_to_cutline ' +
                    '-overwrite ' +
                    '--config GDAL_CACHEMAX 5000 ' +
                    '--config GDAL_PDF_LAYERS "Map_Frame" ' 
                    '--config GDAL_PDF_LAYERS_OFF "Map_Collar,Map_Frame.Projection_and_Grids,Images,Barcode" ' + #note it's important to have the layers grouped into the quotes, together
                    '--config GDAL_PDF_DPI 250 ' +
                    '-wm 5000 ' +
                    '-wo INIT_DEST="255,255,255" ' +
                    '-co "TILED=YES" -co "BIGTIFF=YES" -of GTiff ' +
                    '-co "TFW=YES" ' +
                    '-co "COMPRESS=DEFLATE" ' +
                    '-t_srs EPSG:4326 ' +
                    '-co "PHOTOMETRIC=YCBCR"')
        print(command1)
    
        p1 = sub.Popen(command1, stdout = sub.PIPE,stderr = sub.PIPE, text=True)
        output1, errors1 = p1.communicate()

        # warp_opts = gdal.WarpOptions(
        #                                 cutlineDSName=csvtemppath,
        #                                 overwrite=True,
        #                                 format="GTiff",
        #                                 # cutlineSQL="SELECT cutline FROM table WHERE id=1",
        #                                 # cropToCutline=True,
        #                                 dstSRS="EPSG:4326",
        #                                 outputBounds= '-96.0, 49.0, -94, 50.0',
        #                                 outputBoundsSRS="EPSG:4326",
        #                                 gdal.ParseCommandLine("-co TILED=YES -co COMPRESS=JPEG -co PHOTOMETRIC=YCBCR")
        #                                 # geoloc=True
        #                             )
        
        # ds = gdal.Warp(tifpath_t,pdfpath,options = warp_opts)

    def totiff(self, pdfname, pdfpath, tifpath_t, xmlpath, csvtemppath, gdalpath, xmldict):
    
        # GET PROJECTION
        command0 = (fr'{gdalpath}\gdalsrsinfo.exe "{pdfpath}" -e -o epsg')
        p0 = sub.Popen(command0, stdout = sub.PIPE,stderr = sub.PIPE, universal_newlines=True)
        output0, errors0 = p0.communicate()
        tgtepsg = re.search(r'(EPSG:)(-?\d+)', output0).group(2)
    
        command0 = (fr'{gdalpath}\gdalsrsinfo.exe "{pdfpath}" -e -o all')
        p0 = sub.Popen(command0, stdout = sub.PIPE,stderr = sub.PIPE, universal_newlines=True)
        output0, errors0 = p0.communicate()
        wkt = output0
    
        # EXTRACT XML FILE
        if not os.path.exists(xmlpath) or os.path.getsize(xmlpath) <= 1000:
            pdf = PyPDF2.PdfFileReader(pdfpath)
            catalog = pdf.trailer["/Root"]
            fileNames = catalog['/Names']['/EmbeddedFiles']['/Names']
        
            for i in range(0, len(fileNames)):
                if ".xml"  in str(fileNames[i].getObject()) and r"/EF"  in str(fileNames[i].getObject()) and r"/F" in str(fileNames[i].getObject()):
                    file = fileNames[i].getObject()
                    data = file['/EF']['/F'].getData()
        
                    with open(xmlpath,'w', encoding="utf-8") as f:
                        f.write(data.decode("utf-8"))
                        f.close()
    
        # GET BOUNDING COORDINATES/NEATLINE FROM XML FILE
        '''ds = gdal.Open(pdfpath)
        neatline_wkt = ds.GetMetadataItem("NEATLINE")         # THIS ONE ALSO FROM GDALINFO.EXE DOESN'T WORK AS IT CROPS TO THE EDGE OF THE PDF INSTEAD OF THE IMAGE.'''
    
        westbc = None
        eastbc = None
        northbc = None
        southbc = None
    
        yeardateonmap = None
        yearimprint = None
        yearphotoinsp = None
        yearphotorevis = None
        yearfieldcheck = None
        yearsurvey = None
        yearedit = None
        yearaerial = None
    
        tree = ET.parse(xmlpath)
        root = tree.getroot()
    
        for child in root.iter():
            if child.tag == 'westbc':
                westbc = float(child.text)
            elif child.tag == 'eastbc':
                eastbc = float(child.text)
            elif child.tag == 'northbc':
                northbc = float(child.text)
            elif child.tag == 'southbc':
                southbc = float(child.text)
            elif child.tag == 'procstep':
                if child[0].text.upper().strip() == 'DATE ON MAP':
                    yeardateonmap = child[1].text.strip()
                elif child[0].text.upper().strip() == 'IMPRINT YEAR':
                    yearimprint = child[1].text.strip()
                elif child[0].text.upper().strip() == 'PHOTO INSPECTION YEAR':
                    yearphotoinsp = child[1].text.strip()
                elif child[0].text.upper().strip() == 'PHOTO REVISION YEAR':
                    yearphotorevis = child[1].text.strip()
                elif child[0].text.upper().strip() == 'FIELD CHECK YEAR':
                    yearfieldcheck = child[1].text.strip()                                                                                      
                elif child[0].text.upper().strip() == 'SURVEY YEAR':
                    yearsurvey = child[1].text.strip()
                elif child[0].text.upper().strip() == 'EDIT YEAR':
                    yearedit = child[1].text.strip()
                elif child[0].text.upper().strip() == 'AERIAL PHOTO YEAR':
                    yearaerial = child[1].text.strip()     
    
        neatline_wkt = '"' + f"POLYGON (({eastbc} {southbc}, {eastbc} {northbc}, {westbc} {northbc}, {westbc} {southbc}, {eastbc} {southbc}))" + '"'
        neatline_wkt = '"POLYGON ((-96.0 49.0, -96.0 50.0, -94.0 50.0, -94.0 49.0, -96.0 49.0))"'
        print(neatline_wkt)
    
        '''# CONVERT BOUNDING COORDINATES FROM WGS84 TO PROJCS
        src = osr.SpatialReference()
        src.ImportFromEPSG(4326)                    # WGS84
        tgt = osr.SpatialReference()
        tgt.ImportFromEPSG(tgtepsg)
    
        transform = osr.CoordinateTransformation(src, tgt)
        minx,miny= transform.TransformPoint(southbc, eastbc)[0:2]
        minx,maxy = transform.TransformPoint(northbc, eastbc)[0:2]
        maxx,maxy = transform.TransformPoint(northbc, westbc)[0:2]
        maxx,miny = transform.TransformPoint(southbc, westbc)[0:2]
    
        neatline_wkt = '"' + f"POLYGON (({minx} {miny}, {minx} {maxy}, {maxx} {maxy}, {maxx} {miny}, {minx} {miny}))" + '"'
        print(neatline_wkt)'''
    
        if (not os.path.exists(tifpath_t) and not os.path.exists(tifpath_t[0:-4]+".tfw")) or os.path.getsize(tifpath_t) <= 1000000:
            strt = time.perf_counter()
            # WRITE COORDINATES TO CSV FOR CUTLINES
            with open(csvtemppath,'w') as csv:
                csv.write('id,WKT\n')
                csv.write(f"1,{neatline_wkt}\n")
                csv.close()
        
            # CROP/CONVERT PDF
            # self.cropt(csvtemppath, gdalpath, tifpath_t, pdfpath)
            p1 = mp.Process(target=self.cropt, args=[csvtemppath,gdalpath,tifpath_t,pdfpath])
            p1.start()
            p1.join()
        
            os.remove(csvtemppath)
            fin = time.perf_counter()
            print(f"reworked {pdfname} in {round(fin-strt, 2)} secs  --  {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
    
        # CREATE DICT FOR USE IN METAXLSX FILE
        if os.path.exists(xmlpath):
            xmlFLAG = "Y"
        else:
            xmlFLAG = ""            
        if os.path.exists(tifpath_t):
            topoFLAG = "Y"
        else:
            topoFLAG = ""
        if os.path.exists(tifpath_t[0:-4]+".tfw"):
            t_tfwFLAG = "Y"
        else:
            t_tfwFLAG = ""

        orthoFLAG = ""
        o_tfwFLAG = ""
        xmldict[pdfname] = [topoFLAG, t_tfwFLAG, orthoFLAG, o_tfwFLAG, xmlFLAG, tgtepsg, wkt, neatline_wkt, yeardateonmap, yearimprint, yearphotoinsp, yearphotorevis, yearfieldcheck, yearsurvey, yearedit, yearaerial]

    def main(self, pdfname, pdfpath, tifpath_t, xmlpath, csvtemppath, gdalpath, xmldict):
        try:
            start = time.perf_counter()
            self.totiff(pdfname, pdfpath, tifpath_t, xmlpath, csvtemppath, gdalpath, xmldict)
            finish = time.perf_counter()
            print(f"{pdfname} finished in {round(finish-start, 2)} secs  --  {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())}")
            return xmldict
        except Exception as e:
            print(f"---\nERROR FML {pdfname} \n\t{e}")
            raise

# UNCOMMENT BELOW TO RUN FOR SINGLE PDF
if __name__ == '__main__':
    pdfname = "MI_Escanaba_470714_1957_250000_geo.pdf"
    pdfdirNew = r"F:\A Wong_HTMC_9-30-20"
    tifdirNew = r"\\CABCVAN1FPR009\USGS_Topo\USGS_HTMC_Geotiff\new_htmc"
    mscpath = r"\\cabcvan1gis005\MISC_DataManagement\Data\US\_FED\TOPO\2020_09_18"
    gdalpath = r"C:\Program Files\GDAL"

    pdfpath = os.path.join(pdfdirNew, pdfname[0:-4]+".pdf")
    tifpath_t = os.path.join(tifdirNew, pdfname[0:-4]+"_t.tif")
    xmlpath = os.path.join(tifdirNew,pdfname[0:-4]+".xml")
    csvtemppath = os.path.join(mscpath,pdfname[0:-4]+".csv")
    xmldict = {}

    tp = TOPO_Process()
    tp.main(pdfname, pdfpath, tifpath_t, xmlpath, csvtemppath, gdalpath, xmldict)