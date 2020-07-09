import ConfigParser
configParser = ConfigParser.RawConfigParser()   
# configFilePath = r'F:\ERISServerConfig.ini'
configFilePath = r'\\cabcvan1gis006\GISData\ERISServerConfig.ini'
configParser.read(configFilePath)

reportPath_test = configParser.get('server-config', 'reportPath_test')

print(reportPath_test)