
from collections import OrderedDict
import os

### Credential
oracle_test = r"ERIS_GIS/gis295@GMTESTC.glaciermedia.inc"
oracle_production = r"ERIS_GIS/gis295@GMPRODC.glaciermedia.inc"
### mxd file
connectionPath_prod = r"\\cabcvan1gis007\gptools\RiskScore"
connectionPath_test = r"\\cabcvan1gis006\GISData\RiskScore"
mxd_prod = os.path.join(connectionPath_prod,r"mxd","RiskScore_prod.mxd")
mxd_test = os.path.join(connectionPath_test,r"mxd","RiskScore_test.mxd")
### Report path
report_path_test = r"\\cabcvan1eap006\ErisData\Reports\test\noninstant_reports"
report_path_prod = r"\\cabcvan1eap006\ErisData\Reports\prod\noninstant_reports"
