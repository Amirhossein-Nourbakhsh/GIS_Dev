import arcpy, os,sys,timeit
from imp import reload
file_path =os.path.dirname(os.path.abspath(__file__))
sys.path.insert(1,os.path.join(os.path.dirname(file_path),'DB_Framework'))
import models
import psr_utility as utility
import psr_config as config
import flood_plain
import topo
import relief
import wetland
import geology
import soil
import ogw
import radon
import multi_proc_test
reload(sys)
sys.setdefaultencoding('utf8')

if __name__ == "__main__":
    id = 21021100006
    arcpy.AddMessage('Start PSR report...')
    start = timeit.default_timer()
    # ### set workspace
    arcpy.env.workspace = config.scratch_folder
    arcpy.AddMessage('  -- scratch folder: %s' % config.scratch_folder)
    arcpy.env.overwriteOutput = True
    if not os.path.exists(config.temp_gdb):
        arcpy.CreateFileGDB_management(config.scratch_folder,r"temp")

    ### isntantiate of order class and set order geometry and buffering
    order_obj = models.Order().get_order(int(id))
    if order_obj is not None:
        utility.set_order_geometry(order_obj)
        config.if_multi_page = utility.if_multipage(config.order_geometry_pcs_shp)
        arcpy.AddMessage('  -- multiple pages: %s' % str(config.if_multi_page))
        ### Populate radius list of PSR for this Order object
        order_obj.get_search_radius() # populate search radius
        if len(order_obj.psr.search_radius) > 0:
        ### set type of reports
            if_relief_report = False
            if_topo_report = False
            if_wetland_report = False
            if_flood_report = False
            if_geology_report = False
            if_soil_report = False
            if_ogw_report = False
            if_radon_report = False

            # shaded releif map report
            if if_relief_report:
                relief.generate_relief_report(order_obj)
            # topo map report
            if if_topo_report:
                topo.generate_topo_report(order_obj)
            # Wetland report
            if if_wetland_report:
                wetland.generate_wetland_report(order_obj)
            # flood report
            if if_flood_report:
                flood_plain.generate_flood_report(order_obj)
            # geology report
            if if_geology_report:
                geology.generate_geology_report(order_obj)
            # soil report
            if if_soil_report:
                soil.generate_soil_report(order_obj)
            # oil, gas and water wells report
            if if_ogw_report:
                ogw.generate_ogw_report(order_obj)
            # radon report
            if if_radon_report:
                radon.generate_radon_report(order_obj)
            multi_proc_test.generate_flood_report(order_obj)
        else:
            arcpy.AddMessage('No PSR is availabe for this order')
    else:
        arcpy.AddMessage('This order is not availabe')
    end = timeit.default_timer()
    arcpy.AddMessage(('End PSR report process. Duration:', round(end -start,4)))