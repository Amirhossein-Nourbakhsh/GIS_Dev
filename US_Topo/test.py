import arcpy, os,sys,timeit
from imp import reload
file_path = os.path.dirname(os.path.abspath(__file__))
if 'arcgisserver' in file_path:
    model_path = os.path.join('D:/arcgisserver/directories/arcgissystem/arcgisinput/GPtools/DB_Framework')
else:
    model_path = os.path.join(os.path.dirname(file_path),'DB_Framework')
    
sys.path.insert(1,model_path)
import models

arcpy.AddMessage(file_path)

order_obj = models.Order().get_order(1014804)
arcpy.AddMessage(order_obj.number)