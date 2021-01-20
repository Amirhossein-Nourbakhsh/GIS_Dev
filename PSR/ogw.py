from imp import reload
import arcpy, os, sys
import timeit
import shutil
import psr_utility as utility
import psr_config as config
sys.path.insert(1,os.path.join(os.getcwd(),'DB_Framework'))
reload(sys)
import models
def generate_ogw_report(order_obj):
    arcpy.AddMessage('  -- Start generating PSR Oil, Gas and Water wells map report...')
    start = timeit.default_timer() 
    ### set scratch folder
    arcpy.env.workspace = config.scratch_folder
    arcpy.env.overwriteOutput = True   
    arcpy.AddMessage('      - scratch folder: %s' % config.scratch_folder)
    centre_point = order_obj.geometry.trueCentroid
    elevation = utility.get_elevation(centre_point.X, centre_point.Y)
    if elevation != None:
        centre_point.Z = float(elevation)
    ### create order geometry center shapefile
    order_rows = arcpy.SearchCursor(config.order_geometry_pcs_shp)
    point = arcpy.Point()
    array = arcpy.Array()
    feature_list = []
    arcpy.CreateFeatureclass_management(config.scratch_folder, os.path.basename(config.order_center_pcs), "POINT", "", "DISABLED", "DISABLED", config.spatial_ref_pcs)
    insert_cursor = arcpy.InsertCursor(config.order_center_pcs)
    feat = insert_cursor.newRow()
    for order_row in order_rows:
        # Set X and Y for start and end points
        geometry = order_row.SHAPE
        point.X = geometry.trueCentroid.X
        point.Y = geometry.trueCentroid.Y
        array.add(point)
        center_point = arcpy.Multipoint(array)
        array.removeAll()
        feature_list.append(center_point)
        feat.shape = point
        insert_cursor.insertRow(feat)
    del feat
    del insert_cursor
    del order_row
    del order_rows
    del point
    del array
    ### extract buffer size for flood report
    psr_list = order_obj.get_psr()
    if len(psr_list) > 0:
        buffer_radius = next(psr.search_radius for psr in psr_list if psr.type == order_obj.psr.type)
        
        ds_oid_wells = []
        ds_oid_wells_max_radius = '10093'     # 10093 is a federal source, PWSV
        psr_10093_radius = next(psr.search_radius for psr in psr_list if str(psr.ds_oid) == '10093')
        for psr in psr_list:
            if psr.ds_oid not in ['9334', '10683', '10684', '10685', '10688','10689', '10695', '10696']:       #10695 is US topo, 10696 is HTMC, 10688 and 10689 are radons
                ds_oid_wells.append(psr.ds_oid )
                if (psr.search_radius > psr_10093_radius):
                    ds_oid_wells_max_radius = psr.ds_oid
        merge_list = []
        for ds_oid in ds_oid_wells:
            psr_radius = 0
            buffer_wells = os.path.join(config.scratch_folder,"buffer_" + str(ds_oid) + ".shp")
            psr_radius = next(p.search_radius for p in psr_list if str(p.ds_oid) == str(ds_oid))
            if psr_radius != '' and psr_radius > 0 :
                arcpy.Buffer_analysis(config.order_geometry_pcs_shp, buffer_wells, str(psr_radius) + " MILES")
                wells_clip = os.path.join(config.scratch_folder,'wells_clip_' + str(ds_oid) + '.shp')
                arcpy.Clip_analysis(config.eris_wells, buffer_wells, wells_clip)
                arcpy.Select_analysis(wells_clip, os.path.join(config.scratch_folder,'wells_selected_' + str(ds_oid) + '.shp'), "DS_OID =" + str(ds_oid))
                merge_list.append(os.path.join(config.scratch_folder,'wells_selected_' + str(ds_oid) + '.shp'))
        arcpy.Merge_management(merge_list, config.wells_merge)
        del config.eris_wells
        
        # Calculate Distance with integration and spatial join- can be easily done with Distance tool along with direction if ArcInfo or Advanced license
        wells_merge_pcs= os.path.join(config.scratch_folder,"wells_merge_pcs.shp")
        arcpy.Project_management(config.wells_merge, wells_merge_pcs, config.spatial_ref_pcs)
        arcpy.Integrate_management(wells_merge_pcs, ".5 Meters")
        
        # Add distance to selected wells
        arcpy.SpatialJoin_analysis(wells_merge_pcs, config.order_geometry_pcs_shp, config.wells_sj, "JOIN_ONE_TO_MANY", "KEEP_ALL","#", "CLOSEST","5000 Kilometers", "Distance")   # this is the reported distance
        arcpy.SpatialJoin_analysis(config.wells_sj, config.order_center_pcs, config.wells_sja, "JOIN_ONE_TO_MANY", "KEEP_ALL","#", "CLOSEST","5000 Kilometers", "Dist_cent")  # this is used for mapkey calculation
        
        if int(arcpy.GetCount_management(os.path.join(config.wells_merge)).getOutput(0)) != 0:
            
            arcpy.AddMessage('  - Water Wells section, exists water wells')
            check_field = arcpy.ListFields(config.wells_sja,"Elevation")
            if len(check_field)==0:
                arcpy.AddField_management(config.wells_sja, "Elevation", "DOUBLE", "12", "6", "", "", "NULLABLE", "NON_REQUIRED", "")
            # wells_sja = getElevation(config.wells_sja,["X","Y","ID"])#wells_sja = arcpy.inhouseElevation_ERIS(wells_sja).getOutput(0)

            # elevationArray=[]
            # Call_Google = ''
            # rows = arcpy.SearchCursor(wells_sja)
            # for row in rows:
            #     # print row.Elevation
            #     if row.Elevation == -999:
            #         Call_Google = 'YES'
            #         break
            # del rows
            


    
    
 

    
    
    end = timeit.default_timer()
    arcpy.AddMessage((' -- End generating PSR Oil, Gas and Water wells report. Duration:', round(end -start,4)))