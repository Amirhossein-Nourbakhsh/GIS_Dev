import sys, os, string, arcpy, logging
from arcpy import env, mapping
import time

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
