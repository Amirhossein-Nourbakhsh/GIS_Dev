########################################################
 ## Name: Create ERIS Report and XML
 ## Source Name: Risk_Score_Report.py
 ## Version: ArcGIS 10.8
 ## Author: Hamid Kiavarz
 ##
 ## Description: Generates the PDF file for the Risk reports.
 ## Date July 2020
 ##############################################u##########

# Import required modules
import json,timeit
import cx_Oracle, urllib, glob
import arcpy, os, numpy
from datetime import datetime
import RiskScore_Config


class Oracle:
     # static variable: oracle_functions
     def __init__(self,machine_name):
         # initiate connection credential
         if machine_name.lower() =='test':
             self.oracle_credential = RiskScore_Config.oracle_test
         elif machine_name.lower()=='prod':
             self.oracle_credential = RiskScore_Config.oracle_production
         else:
          raise ValueError("Bad machine name")
     def connect_to_oracle(self):
         try:
             self.oracle_connection = cx_Oracle.connect(self.oracle_credential)
             self.cursor = self.oracle_connection.cursor()
         except cx_Oracle.Error as e:
             print(e,'Oralce connection failed, review credentials.')
     def close_connection(self):
         self.cursor.close()
         self.oracle_connection.close()
     def call_function(self,function_name,request_Id):
            self.connect_to_oracle()
            cursor = self.cursor
            try:
                outType = cx_Oracle.CLOB
                inputParameters = [request_Id]
                output = json.loads(cursor.callfunc(function_name,outType,inputParameters).read())
                return output
            except cx_Oracle.Error as e:
                raise Exception(("Oracle Failure",e.message.message))
            except Exception as e:
                raise Exception(("JSON Failure",e.message))
            except NameError as e:
                raise Exception("Bad Function")
            finally:
               self.close_connection()
def copyMXD_to_Scratch(request_Id, mxd):
    try:
        mxdDoc = arcpy.mapping.MapDocument(mxd)
        scratch = arcpy.env.scratchFolder
        mxd_name = "RiskScore" + "_" + str(request_Id) + ".mxd"
        copied_mxd = mxdDoc.saveACopy(os.path.join(scratch, mxd_name))
        del mxdDoc
        return arcpy.mapping.MapDocument(os.path.join(scratch, mxd_name))
    except :
        msgs = "ArcPy ERRORS:\n %s\n"%arcpy.GetMessages(2)
        arcpy.AddError(msgs)
        raise
def setDefinitionQuery(inputMXD,request_Id):
    try:
        detail_lyr = None
        geo_lyr = None
        for layer in arcpy.mapping.ListLayers(inputMXD):
            if layer.name == 'RISK_SCORE_DETAIL': # incedents layers
                detail_lyr = layer
                detail_lyr.definitionQuery = "REQUEST_ID = {} AND INCIDENT_PERMIT IS NOT NULL".format(str(request_Id))
            if layer.name == 'RISK_SCORE_GEOMETRY': # include cenetr points of request for risk report
                geo_lyr = layer
                geo_lyr.definitionQuery = "REQUEST_ID = {}".format(str(request_Id))
        
        inputMXD.save()
        del inputMXD
        
        return geo_lyr
    except :
        msgs = "ArcPy ERRORS:\n %s\n"%arcpy.GetMessages(2)
        arcpy.AddError(msgs)
        raise
def updateTempleteElements(input_mxdDoc,input_json):
    
    ### get templete elements
    total_count_elm = arcpy.mapping.ListLayoutElements(input_mxdDoc, "TEXT_ELEMENT", "Total_count")[0]
    address_elm = arcpy.mapping.ListLayoutElements(input_mxdDoc, "TEXT_ELEMENT", "AddressText")[0]
    incident_site_elm = arcpy.mapping.ListLayoutElements(input_mxdDoc, "TEXT_ELEMENT", "Incident_site")[0]
    incident_surround_elm = arcpy.mapping.ListLayoutElements(input_mxdDoc, "TEXT_ELEMENT", "Incident_surround")[0]
    permit_site_elm = arcpy.mapping.ListLayoutElements(input_mxdDoc, "TEXT_ELEMENT", "Permit_site")[0]
    permit_surround_elm = arcpy.mapping.ListLayoutElements(input_mxdDoc, "TEXT_ELEMENT", "Permit_surround")[0]
    
    ### set element value by request information
    total_count_elm.text = "This report found  %s environmental records within 1/8 mile of the property located at:  "%input_json['TOTAL_POINTS']
    address_elm.text = input_json['ADDRESS']
    incident_site_elm.text = input_json['TOTAL_ONSITE_INC']
    incident_surround_elm.text = input_json['TOTAL_OFFSITE_INC']
    permit_site_elm.text = input_json['TOTAL_ONSITE_PER']
    permit_surround_elm.text = input_json['TOTAL_OFFSITE_PER']
    input_mxdDoc.save()
    del input_mxdDoc
def zoomToRiskGeometry(input_mxd,geometry_lyr ):
    df = arcpy.mapping.ListDataFrames(input_mxd,"*")[0]
    
    extent = geometry_lyr.getExtent()
    df.extent = extent
    df.scale = 4000
    input_mxd.save()
    del input_mxd
    
    
if __name__ == '__main__':
    
    ### input parameters
    request_Id = arcpy.GetParameterAsText(0)               
    startTotal = timeit.default_timer()
    ###input RequestId
    request_Id = 701
    env = 'prod'
    ws = arcpy.env.scratchFolder
    arcpy.env.overwriteOutput = True   
    arcpy.env.workspace = ws
    
    mxd = ""
    reportpath = ""
    if env == 'test':
        reportpath = RiskScore_Config.report_path_test
        mxd = RiskScore_Config.mxd_test
    elif env == 'prod':
        reportpath = RiskScore_Config.report_path_prod
        mxd = RiskScore_Config.mxd_prod
    ### copy mxd file from original file to scratch folder
    copied_mxd = copyMXD_to_Scratch(request_Id, mxd)
    ### Set definition query
    geometry_lyr = setDefinitionQuery(copied_mxd,request_Id)
    ### get request information from DB
    request_json = Oracle(env).call_function('ERIS_RISK_SCORE.getRiskScoreDetail',int(str(request_Id)))
    ### update templete element contents
    updateTempleteElements(copied_mxd,request_json)
    ### Set dataframe scale and zoom to request centre point
    zoomToRiskGeometry(copied_mxd,geometry_lyr)
    
    # ### generate final report
    outputLayoutPDF = os.path.join(reportpath, "RiskScore_Map_" + str(request_Id) + ".pdf")
    arcpy.mapping.ExportToPDF(copied_mxd, outputLayoutPDF, "PAGE_LAYOUT", 640, 480, 250, "BEST", "RGB", True, "ADAPTIVE", "RASTERIZE_BITMAP", False, True, "LAYERS_AND_ATTRIBUTES", True, 90)
    
    arcpy.AddMessage("Output Report: %s"%outputLayoutPDF)
    arcpy.SetParameterAsText(1,outputLayoutPDF)
     
    endTotal= timeit.default_timer()
    arcpy.AddMessage(('Total Duration:', round(endTotal -startTotal,4)))