# -*- coding: utf-8 -*-


import os
from math import ceil

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from qgis.core import QgsMapLayerRegistry

from geosurf.qgs_tools import loaded_point_layers, get_point_data
from geosurf.utils import is_number
from mpl.mpl_widget import MplMainWidget, plot_line


       
class EqHazard_QWidget( QWidget ):
    
      
    
    def __init__( self, canvas, plugin_name ):

        super( EqHazard_QWidget, self ).__init__() 
        self.mapcanvas = canvas        
        self.plugin_name = plugin_name 
        
        self.plot_undefined_choice_txt = "not defined"
        self.plot_density_choice_txt = "density"
        self.plot_velocities_choice_txt = "velocities"
        self.plot_Qvalues_choice_txt = "Q values"
                
        self.config_plot_options = [self.plot_undefined_choice_txt,
                                   self.plot_density_choice_txt,
                                   self.plot_velocities_choice_txt,
                                   self.plot_Qvalues_choice_txt]
        
        self.thickness_field_name = "thk (km)"
        self.density_field_name = "rho"
        self.velocity_p_field_name = "Vp (km/s)"
        self.velocity_s_field_name = "Vs (km/s)"
        self.q_p_field_name = "Qp"                
        self.q_s_field_name = "Qs"  
        self.depth_field_name = "depth (km)"
        self.layer_field_name = "layer"
        
        self.input_field_names = [self.thickness_field_name,
                                  self.density_field_name,
                                  self.velocity_p_field_name,
                                  self.velocity_s_field_name,
                                  self.q_p_field_name,
                                  self.q_s_field_name,
                                  self.depth_field_name,
                                  self.layer_field_name]
        
        
        
        self.plot_configs_ok = False
        
        self.plot_windows = []
               
        self.setup_gui()

                      
    def setup_gui( self ): 

        self.dialog_layout = QHBoxLayout()
        
        self.dialog_layout.addWidget( self.setup_inputdata() )
        self.dialog_layout.addWidget( self.setup_processing() )        
                                                           
        self.setLayout(self.dialog_layout)            
        self.adjustSize()               
        self.setWindowTitle(self.plugin_name)        
  

    def setup_inputdata(self):
        
        input_QGroupBox = QGroupBox("Input")
        
        layout = QVBoxLayout() 
        
        self.read_input_data_QPushButton = QPushButton(self.tr("Read input file"))  
        self.read_input_data_QPushButton.clicked.connect( self.get_input_data ) 
        layout.addWidget(self.read_input_data_QPushButton )
        
        input_QGroupBox.setLayout(layout)
        
        return input_QGroupBox
  
  
    def setup_processing(self):
        
        processing_QGroupBox = QGroupBox("Processing")
        
        layout = QGridLayout()

        self.configure_plot_QPushButton = QPushButton(self.tr("Configure plot"))          
        self.configure_plot_QPushButton.clicked.connect( self.get_plot_configuration )         
        layout.addWidget(self.configure_plot_QPushButton, 0, 0, 1, 1 )        
 
        self.plot_data_QPushButton = QPushButton(self.tr("Plot data"))          
        self.plot_data_QPushButton.clicked.connect( self.plot_geodata )         
        layout.addWidget(self.plot_data_QPushButton, 0, 1, 1, 1 ) 
                       
        processing_QGroupBox.setLayout(layout)
        
        return processing_QGroupBox
    

    def get_input_data( self ):
        
        if len(loaded_point_layers()) == 0:
            self.warn("No point layer loaded")
            return
        
        dialog = SourceDataDialog()

        if dialog.exec_():
            try:
                self.point_layer, self.link_name_field = self.extract_input_data( dialog )
            except:
                self.warn( "Error in input")
                return 
        else:
            self.warn( "Nothing defined")
            return
        
       
    def get_plot_configuration(self):
        
        dialog = PlotConfigDialog( self.config_plot_options )
        
        if dialog.exec_():
            try:
                self.bottom_variables, self.top_variables = self.extract_plot_config(dialog)
            except:
                self.warn("Error in plot configuration")
                return
        else:
            self.warn("Undefined plot configuration")
            return
        
        if self.bottom_variables == self.plot_undefined_choice_txt and \
           self.top_variables == self.plot_undefined_choice_txt:
            self.warn("No choice for plot configuration")
            self.plot_configs_ok = False
        elif self.bottom_variables == self.top_variables:
            self.warn("Choose different variables")
            self.plot_configs_ok = False            
        else:
            self.plot_configs_ok = True
            

    def extract_plot_config(self, dialog):
        
        bottom_variables = dialog.bottom_variables_QComboBox.currentText()
        top_variables = dialog.top_variables_QComboBox.currentText()       
        
        return bottom_variables, top_variables
        
         
    def extract_input_data(self, dialog ):
        
        point_layer = dialog.point_layer        
        field_undefined_txt = dialog.field_undefined_txt
        link_name_field = self.parse_field_choice(dialog.link_field_QComboBox.currentText(), field_undefined_txt)
          
        return point_layer, link_name_field 
    

    def parse_field_choice(self, val, choose_message):
        
        if val == choose_message:
            return None
        else:
            return val
    

    def plot_geodata(self):
        
        try:
            point_layer, link_name_field = self.point_layer, self.link_name_field
        except:
            self.warn("Input data are not defined")
            return
        
        if not self.plot_configs_ok:
            self.warn("Undefined plot configurations")
            return
        else:
            bottom_variables, top_variables = self.bottom_variables, self.top_variables
        
        
        _, rec_values_Lst2 = get_point_data( point_layer, [link_name_field])
        ifile_paths = [rec_values[-1] for rec_values in rec_values_Lst2]
        
        geodata = []
        for ifile_path in ifile_paths:
            geodata_rec = self.read_hazard_input_file(ifile_path)
            if geodata_rec is None:
                return
            else:
                geodata.append(geodata_rec)
                
        assert len(geodata) > 0
        
        geodata_names = self.extract_data_names(ifile_paths)
        # create plot window
        plot_window = MplMainWidget()  
        
        for n, (geodata_unit, geodata_name) in enumerate(zip(geodata,geodata_names)): 
            subplot_code = self.get_subplot_code(len(geodata), n+1)
             
            self.plot_geodata_unit(plot_window, 
                                   bottom_variables,
                                   top_variables, 
                                   geodata_unit,
                                   geodata_name, 
                                   subplot_code)
            
        plot_window.canvas.draw() 
        
        self.plot_windows.append( plot_window )


    def extract_data_names(self, ifile_paths):
        
        return [ifile_path.split(os.sep)[-1].split(".")[0] for ifile_path in ifile_paths]


    def get_subplot_code(self, n_recs, n_rec):

        n_rows = (n_recs + 1) / 2
        n_cols = 2
        
        subplot_code = int("%d%d%d" % (n_rows, n_cols, n_rec))
        return subplot_code
        
        
    def read_hazard_input_file(self, file_path):
        
        def parse_hazard_input_data(in_data_list2):
            
            data_dict = {} # a dict that will contain the lists of values for each field
            
            for fld_name in fld_names:
                data_dict[fld_name] = []
            
            for rec_vals in in_data_list2:
                assert len(fld_names) == len(rec_vals)
                for fld_name, val in zip(fld_names, rec_vals):
                    data_dict[fld_name].append(float(val))
                    
            return data_dict


        def extract_number_values(indata_raw):
            
            for n, indata_row in enumerate(indata_raw):
                indata_vals = indata_row.split()
                are_numbers = map(is_number, indata_vals)
                if reduce(lambda a, b: a and b, are_numbers):
                    return n, indata_raw[n:]
            
        try:
            with open(file_path, "r") as ifile:
                indata_raw = ifile.readlines()
        except:
            self.warn("Unable to read input file: %s" % (file_path))
            return None
        

        ifile_skip_lines, in_data_vals = extract_number_values(indata_raw)
        
        fld_names = self.input_field_names
        flds_num = len(fld_names)
        in_data_list2 = []        
        for n, in_data_val in enumerate(in_data_vals):
            rec_vals = in_data_val.split()
            if len(rec_vals) != flds_num:
                self.warn("Rec # %d in file %s has only %d values instead of %d required" % \
                          (ifile_skip_lines + n + 1,
                          file_path,
                          len(rec_vals),
                          flds_num))
                return None
            in_data_list2.append(rec_vals)
            
        if len(in_data_list2) == 0:
                self.warn("No recs found in file %s" % (file_path))
                return None            
        else:
            return parse_hazard_input_data(in_data_list2)
                

    def create_axes(self, subplot_code, plot_window, geodata_name, plot_x_range, plot_y_range ):

        axes = plot_window.canvas.fig.add_subplot( subplot_code )
        
        y_min, y_max = plot_y_range
        axes.set_ylim( y_min, y_max )        
        if plot_x_range is not None:
            x_min, x_max = plot_x_range
            axes.set_xlim( x_min, x_max )

        axes.set_title(geodata_name,  y=1.40)
        axes.grid(True)
                           
        return axes


    def extract_values(self, geodata_unit, variables):
        
        if variables == self.plot_density_choice_txt:
            return [geodata_unit[self.density_field_name]]
        elif variables == self.plot_velocities_choice_txt:
            return [geodata_unit[self.velocity_p_field_name], geodata_unit[self.velocity_s_field_name]]
        elif variables == self.plot_Qvalues_choice_txt:
            return [geodata_unit[self.q_p_field_name], geodata_unit[self.q_s_field_name]]  
        else:
            return []  


    def variable_legend_label(self, variable_x):

        density_legend = ["density"]
        velocity_legend = ["Vp", "Vs"]
        Q_vals_legend = ["Qp", "Qs"]
                
        if variable_x == self.plot_density_choice_txt:
            return density_legend
        elif variable_x == self.plot_velocities_choice_txt:
            return velocity_legend
        elif variable_x == self.plot_Qvalues_choice_txt:
            return Q_vals_legend
        elif variable_x == self.plot_undefined_choice_txt:        
            return []  
        

    def variable_label(self, variable_x):

        density_label = "density [g/cm3]"
        velocity_label = "v [km/s]"
        Q_vals_label = "Q value"
                
        if variable_x == self.plot_density_choice_txt:
            return density_label
        elif variable_x == self.plot_velocities_choice_txt:
            return velocity_label
        elif variable_x == self.plot_Qvalues_choice_txt:
            return Q_vals_label
        elif variable_x == self.plot_undefined_choice_txt:        
            return ""        


    def extract_values_range(self, variable_x, geodata_unit):
                
        if variable_x == self.plot_density_choice_txt:
            return self.get_data_range( geodata_unit[self.density_field_name] )
        elif variable_x == self.plot_velocities_choice_txt:
            return self.get_data_range( geodata_unit[self.velocity_p_field_name] + geodata_unit[self.velocity_s_field_name])
        elif variable_x == self.plot_Qvalues_choice_txt:
            return self.get_data_range( geodata_unit[self.q_p_field_name] + geodata_unit[self.q_s_field_name])
        elif variable_x == self.plot_undefined_choice_txt:        
            return None
    
    
    def create_plot_lines(self, axes, geodata_unit, variables, colors):
        
        var_values = self.extract_values(geodata_unit, variables)
        variable_y = geodata_unit[self.depth_field_name]   
        lines = []
        for variable_x, color in zip(var_values, colors):
            lines.append( plot_line(axes,
                         variable_x, 
                         variable_y, 
                         color,
                         drawstyle = "steps-pre") )

        return lines        
        

    def plot_geodata_unit(self, plot_window, variables_x_btm, variables_x_top, geodata_unit, geodata_name, subplot_code):
        
        depth_label = "depth [km]"
        depth_vals = geodata_unit[self.depth_field_name]
        
        
        var_x_btm_label = self.variable_label( variables_x_btm)
        var_x_top_label = self.variable_label( variables_x_top)
        
        plot_x_btm_range = self.extract_values_range(variables_x_btm, geodata_unit)          
        plot_x_top_range = self.extract_values_range(variables_x_top, geodata_unit)
        
        plot_y_range = self.get_data_range(geodata_unit[self.depth_field_name]) 
            
        btm_axes = self.create_axes( subplot_code,
                                  plot_window, 
                                  geodata_name,
                                  plot_x_btm_range, 
                                  plot_y_range  )             
              
        btm_axes.set_xlabel(var_x_btm_label)
        btm_axes.set_ylabel(depth_label) 

        btm_axes.invert_yaxis()         
        plot_window.canvas.fig.tight_layout(pad=0.1, w_pad=0.05, h_pad=1.0)
        
        colors_x_btm = ["brown", "green"]
        bottom_lines = self.create_plot_lines(btm_axes, geodata_unit, variables_x_btm, colors_x_btm)

 
        if plot_x_top_range is not None:
            top_axes = btm_axes.twiny()
            top_axes.set_xlim( *plot_x_top_range )
            top_axes.set_xlabel(var_x_top_label)
            colors_x_top = ["red", "blue"]
            top_lines = self.create_plot_lines(top_axes, geodata_unit, variables_x_top, colors_x_top)


        var_x_btm_legend_label = self.variable_legend_label( variables_x_btm)
        var_x_top_legend_label = self.variable_legend_label( variables_x_top) 
 
        if plot_x_top_range is None:
            plot_window.canvas.fig.legend(bottom_lines, var_x_btm_legend_label)
        else:
            plot_window.canvas.fig.legend(bottom_lines + top_lines, var_x_btm_legend_label + var_x_top_legend_label)            
                      
                        
        """

        plot_v_range = self.get_data_range(geodata_unit["Vp (km/s)"] + geodata_unit["Vs (km/s)"])
        top_axes.set_xlim(plot_v_range)
       
        top_axes.set_xlabel('v [km/s]')
   
        vp_line = plot_line( top_axes,
                            geodata_unit["Vp (km/s)"], 
                            y_vals, 
                            "red",
                            drawstyle = "steps-pre")     
            
        vs_line = plot_line( top_axes,
                            geodata_unit["Vs (km/s)"], 
                            y_vals, 
                            "blue",
                            drawstyle = "steps-pre")  
       
        """
        
        
        
    def plot_data_unit(self, plot_window, geodata_unit, geodata_name, subplot_code):
        
        plot_depth_range = self.get_data_range(geodata_unit["depth (km)"])
        
        plot_dens_range = self.get_data_range(geodata_unit["rho"])        
        
        btm_axes = self.create_axes( subplot_code,
                                  plot_window, 
                                  geodata_name,
                                  plot_dens_range, 
                                  plot_depth_range  ) 
        
        btm_axes.invert_yaxis()       
        btm_axes.set_xlabel('density [g/cm3]')
        btm_axes.set_ylabel('depth [km]') 
        
        plot_window.canvas.fig.tight_layout(pad=0.1, w_pad=0.05, h_pad=1.0)
        
        y_vals = geodata_unit["depth (km)"]
                
        dens_line = plot_line( btm_axes,
                            geodata_unit["rho"], 
                            y_vals, 
                            "brown",
                            drawstyle = "steps-pre")    
        

        top_axes = btm_axes.twiny()

        plot_v_range = self.get_data_range(geodata_unit["Vp (km/s)"] + geodata_unit["Vs (km/s)"])
        top_axes.set_xlim(plot_v_range)
       
        top_axes.set_xlabel('v [km/s]')
   
        vp_line = plot_line( top_axes,
                            geodata_unit["Vp (km/s)"], 
                            y_vals, 
                            "red",
                            drawstyle = "steps-pre")     
            
        vs_line = plot_line( top_axes,
                            geodata_unit["Vs (km/s)"], 
                            y_vals, 
                            "blue",
                            drawstyle = "steps-pre")  

             
        plot_window.canvas.fig.legend([dens_line, vp_line, vs_line], ['density', 'Vp', 'Vs'])
                      
        
    def get_data_range(self, data_list):
        
        if data_list is None:
            return None
        elif data_list == []:
            return None
        else:
            return 0, ceil(max(data_list))
                
        
    def info(self, msg):
        
        QMessageBox.information( self,  self.plugin_name, msg )
        
        
    def warn( self, msg):
    
        QMessageBox.warning( self,  self.plugin_name, msg )
        
        
        
class SourceDataDialog( QDialog ):
    
    
    def __init__(self, parent=None):
                
        super( SourceDataDialog, self ).__init__(parent)
        
        self.setup_gui()
        
        
    def setup_gui(self):        
        
        self.layer_choose_msg = "choose"
        self.field_undefined_txt = "---"
 
        layout = QGridLayout()
                        
        # input layer
        
        layer_QGroupBox = QGroupBox("Input point layer")
        layer_QGridLayout = QGridLayout() 
        
        self.input_layers_QComboBox = QComboBox()
        layer_QGridLayout.addWidget(self.input_layers_QComboBox, 0,0,1,2) 
        
        layer_QGroupBox.setLayout(layer_QGridLayout)              
        layout.addWidget(layer_QGroupBox, 0,0,1,2)          

        # link field
                
        linkfield_QGroupBox = QGroupBox("Link field")
        linkfield_QGridLayout = QGridLayout()    

        self.link_field_QComboBox = QComboBox()

        linkfield_QGridLayout.addWidget(self.link_field_QComboBox, 0,0,1,1)   

        linkfield_QGroupBox.setLayout(linkfield_QGridLayout)              
        layout.addWidget(linkfield_QGroupBox, 1,0,2,2)
             
                
        self.refresh_input_layer_combobox()
        
        self.input_layers_QComboBox.currentIndexChanged[int].connect(self.refresh_link_field_combobox )
        
        okButton = QPushButton("&OK")
        cancelButton = QPushButton("Cancel")

        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)
              
        layout.addLayout( buttonLayout, 5, 0, 1, 2 )
        
        self.setLayout( layout )

        self.connect(okButton, SIGNAL("clicked()"),
                     self,  SLOT("accept()") )
        self.connect(cancelButton, SIGNAL("clicked()"),
                     self, SLOT("reject()"))
        
        self.setWindowTitle("Source layer")



    def refresh_input_layer_combobox(self):

        self.pointLayers = loaded_point_layers()
        self.input_layers_QComboBox.clear()        
        
        self.input_layers_QComboBox.addItem( self.layer_choose_msg )
        self.input_layers_QComboBox.addItems( [ layer.name() for layer in self.pointLayers ] ) 
        
        self.reset_link_field_combobox()
         
         
    def reset_link_field_combobox(self):        
        

        self.link_field_QComboBox.clear()
        self.link_field_QComboBox.addItem(self.field_undefined_txt)
            
                     
    def refresh_link_field_combobox( self ):
        
        self.reset_link_field_combobox()

        point_shape_qgis_ndx = self.input_layers_QComboBox.currentIndex() - 1
        if point_shape_qgis_ndx == -1:
            return
        
        self.point_layer = self.pointLayers[ point_shape_qgis_ndx ]
       
        point_layer_field_list = self.point_layer.dataProvider().fields().toList( ) 
               
        field_names = [field.name() for field in point_layer_field_list]
        
        self.link_field_QComboBox.addItems(field_names)

    

class PlotConfigDialog( QDialog ):
    
        
            
    def __init__(self, config_plot_options, parent=None):
                
        super( PlotConfigDialog, self ).__init__(parent)
        
        self.config_plot_options = config_plot_options
        
        self.setup_gui()
        
        
    def setup_gui(self):        
        
 
        layout = QGridLayout()
                        
        # plot variables
        
        variables_QGroupBox = QGroupBox("Variables to plot")
        variables_QGridLayout = QGridLayout() 

        variables_QGridLayout.addWidget(QLabel("Variable(s)"), 0,0,1,1)         
        self.bottom_variables_QComboBox = QComboBox()
        variables_QGridLayout.addWidget(self.bottom_variables_QComboBox, 0,1,1,1) 
  
        variables_QGridLayout.addWidget(QLabel("Additional variable(s)"), 1,0,1,1)         
        self.top_variables_QComboBox = QComboBox()
        variables_QGridLayout.addWidget(self.top_variables_QComboBox, 1,1,1,1) 
              
        variables_QGroupBox.setLayout(variables_QGridLayout)              
        layout.addWidget(variables_QGroupBox, 0,0,1,2)          
   
        self.populate_config_plot_combobox()
        
        okButton = QPushButton("&OK")
        cancelButton = QPushButton("Cancel")

        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch()
        buttonLayout.addWidget(okButton)
        buttonLayout.addWidget(cancelButton)
              
        layout.addLayout( buttonLayout, 5, 0, 1, 2 )
        
        self.setLayout( layout )

        self.connect(okButton, SIGNAL("clicked()"),
                     self,  SLOT("accept()") )
        self.connect(cancelButton, SIGNAL("clicked()"),
                     self, SLOT("reject()"))
        
        self.setWindowTitle("Plot variables")



    def populate_config_plot_combobox(self):
        
        self.bottom_variables_QComboBox.insertItems(0, self.config_plot_options[1:])
        self.top_variables_QComboBox.insertItems(0, self.config_plot_options) 
              


        


