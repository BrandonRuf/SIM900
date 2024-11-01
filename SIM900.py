import numpy   as _n
import time    as _t
import spinmob as _s
import time    as _time
import spinmob.egg as _egg
_g = _egg.gui
import mcphysics as _mp
from SIM900_api import SIM900_api

try: from . import _visa_tools
except: _visa_tools = _mp.instruments._visa_tools
_debug_enabled = True


_DEBUG = True

class SIM900(_g.BaseObject):
    """
    Graphical front-end for the SIM900 Mainframe w/SIM922 Diode temperature module

    Parameters
    ----------
    autosettings_path='SIM900'
        Which file to use for saving the gui stuff. This will also be the first
        part of the filename for the other settings files.

    pyvisa_py=False
        Whether to use pyvisa_py or not.

    block=False
        Whether to block the command line while showing the window.
    """
    def __init__(self, autosettings_path='SIM900', pyvisa_py=False, block=False):
        if not _mp._visa: _s._warn('You need to install pyvisa to use the SIM900 Mainframe.')

        # No scope selected yet
        self.api = None

        # Internal parameters
        self._pyvisa_py = pyvisa_py

        # Build the GUI
        self.window    = _g.Window('SIM900', autosettings_path=autosettings_path+'_window')
        self.window.event_close = self.event_close
        self.grid_top  = self.window.place_object(_g.GridLayout(False))
        self.window.new_autorow()
        self.grid_bot  = self.window.place_object(_g.GridLayout(False), alignment=0)

        self.button_connect   = self.grid_top.place_object(_g.Button('Connect', True, False))

        self.button_acquire = self.grid_top.place_object(_g.Button('Acquire',True).disable())
        self.label_dmm_name = self.grid_top.place_object(_g.Label('Disconnected'))

        self.settings  = self.grid_bot.place_object(_g.TreeDictionary(),alignment=0).set_width(250)
        self.tabs_data = self.grid_bot.place_object(_g.TabArea(autosettings_path+'_tabs_data.txt'), alignment=0)
        self.tab_raw   = self.tabs_data.add_tab('Raw Data')
        

        self.label_path = self.tab_raw.add(_g.Label('Output Path:').set_colors('cyan' if _s.settings['dark_theme_qt'] else 'blue'))
        self.tab_raw.new_autorow()

        self.plot_raw  = self.tab_raw.place_object(_g.DataboxPlot('*.csv', autosettings_path+'_plot_raw.txt', autoscript=1), alignment=0)
       
        self.grid_bot.set_column_stretch(1,1)
        # Create a resource management object to populate the list
        if _mp._visa:
            if pyvisa_py: self.resource_manager = _mp._visa.ResourceManager('@py')
            else:         self.resource_manager = _mp._visa.ResourceManager()
        else: self.resource_manager = None

        # Populate the list.
        names = []
        if self.resource_manager:
            for x in self.resource_manager.list_resources():
                if self.resource_manager.resource_info(x).alias:
                    names.append(str(self.resource_manager.resource_info(x).alias))
                else:
                    names.append(x)
        self.settings.set_minimum_width(200)
        # VISA settings
        self.settings.add_parameter('VISA/Device', type='list',default_list_index=4, values=['Simulation']+names)
        
        
        # SIM922 settings
        self.settings.add_parameter('SIM922/ID', '', readonly=True)
        self.settings.add_parameter('SIM922/Port', '', readonly=True)
        self.settings.add_parameter('SIM922/Channels/1', False)
        self.settings.add_parameter('SIM922/Channels/2', False)
        self.settings.add_parameter('SIM922/Channels/3', False)
        self.settings.add_parameter('SIM922/Channels/4', False)
        
        self.settings.add_parameter('SIM970/ID', '', readonly=True)
        self.settings.add_parameter('SIM970/Port', '', readonly=True)
        self.settings.add_parameter('SIM970/Channels/1', False)
        self.settings.add_parameter('SIM970/Channels/2', False)
        self.settings.add_parameter('SIM970/Channels/3', False)
        self.settings.add_parameter('SIM970/Channels/4', False)
        
        # Make things easier
        d = self.settings
        
        # Connect all the signals
        self.button_connect.signal_clicked.connect(self._button_connect_clicked)
        self.button_acquire.signal_clicked.connect(self._button_acquire_clicked)
        self.settings.connect_signal_changed("SIM922/Channels/1",self.sim922_refresh)
        self.settings.connect_signal_changed("SIM922/Channels/2",self.sim922_refresh)
        self.settings.connect_signal_changed("SIM922/Channels/3",self.sim922_refresh)
        self.settings.connect_signal_changed("SIM922/Channels/4",self.sim922_refresh)

        # Run the base object stuff and autoload settings
        _g.BaseObject.__init__(self, autosettings_path=autosettings_path)

        self.load_gui_settings()

        # Show the window.
        self.window.show(block)

    def _button_connect_clicked(self, *a):
        """
        Connects or disconnects the VISA resource.
        """

        # If we're supposed to connect
        if self.button_connect.get_value():

            # Close it if it exists for some reason
            if not self.api == None: self.api.close()

            # Make the new one
            self.api = SIM900_api(self.settings['VISA/Device'], self._pyvisa_py)

            # Tell the user what dmm is connected
            if self.api.instrument == None:
                self.label_dmm_name.set_text('*** Simulation Mode ***')
                self.label_dmm_name.set_colors('pink' if _s.settings['dark_theme_qt'] else 'red')
                self.button_connect.set_colors(background='pink')
            else:
                self.label_dmm_name.set_text(self.api.id)
                self.label_dmm_name.set_colors('blue')
            
            '''scan = self.api.scanPorts()
            loc = [i for i in range(len(scan)) if scan[i] != None]
            
            for i in loc:
                if scan[i] == 'SIM922': self.settings["SIM922/Port"] = i+1
                if scan[i] == 'SIM970': self.settings["SIM970/Port"] = i+1'''
                
            self.settings["SIM922/Port"] = 1
            self.settings["SIM970/Port"] = 7
            
            self.SIM922 = self.api.SIM922_api(self.api, port = int(self.settings["SIM922/Port"]))
            self.SIM970 = self.api.SIM970_api(self.api, port = int(self.settings["SIM970/Port"]))
            
            # Check Module IDs
            self.settings["SIM922/ID"] = self.SIM922.getID()
            self.settings["SIM970/ID"] = self.SIM970.getID()
            
            # Get the on/off status of the 4 SIM922 channels
            ex = self.SIM922.getExcitation()
            
            # Set the channel on/off status in the GUI
            self.settings.block_signals()
            for n in range(4):
                self.settings["SIM922/Channels/%d"%(n+1)] = int(ex[n])
            self.settings.unblock_signals()

            # Enable the Acquire button
            self.button_acquire.enable()

        elif not self.api == None:

            # Close down the instrument
            if not self.api.instrument == None:
                self.api.close()
            self.api = None
            self.label_dmm_name.set_text('Disconnected')
            self.settings['SIM922/ID'] = ''
            self.settings['SIM970/ID'] = ''

            # Make sure it's not still red.
            self.label_dmm_name.set_style('')
            self.button_connect.set_colors(background='')

            # Disable the acquire button
            self.button_acquire.disable()

    def _button_acquire_clicked(self, *a):
        """
        Get the enabled curves, storing them in plot_raw.
        """
        _debug('_button_acquire_clicked()')

        # Don't double-loop!
        if not self.button_acquire.is_checked(): return

        # Don't proceed if we have no connection
        if self.api == None:
            self.button_acquire(False)
            return
        
        # Ask the user for the dump file
        self.path = _s.dialogs.save('*.csv', 'Select an output file.', force_extension='*.csv')
        if self.path == None:
            self.button_acquire(False)
            self.settings.enable()
            return

        # Update the label
        self.label_path.set_text('Output Path: ' + self.path)

        _debug('\t path='+repr(self.path))

        # Disable the connection button
        self._set_acquisition_mode(True)

        # For easy coding
        d = self.plot_raw

        # Set up the databox columns
        _debug('\t Setting up databox')
        d.clear()
        
        # Time column
        d['t'] = []
        
        # SIM922 and SIM970 channel columns
        for n in range(4):
            if self.settings["SIM922/Channels/%d"%(n+1)]: 
                d['v22_'+str(n+1)] = []
                
        for n in range(4):
            if self.settings["SIM970/Channels/%d"%(n+1)]: 
                d['v70_'+str(n+1)] = []
        
        # Reset the clock and record it as header
        self.api._t0 = _time.time()
        self._dump(['Date:', _time.ctime()], 'w')
        self._dump(['Time:', self.api._t0])
        
        # And the column labels!
        self._dump(self.plot_raw.ckeys)
        
        # Loop until the user quits
        _debug('  starting the loop')
        while self.button_acquire.is_checked():

            # Ask for the SIM922 and SIM970 channel data (all four channels)
            self.SIM922.write("VOLT? 0")
            self.SIM970.write("VOLT? 0")
            
            # Wait for bytes to arrive in the host queue 
            for i in range(3):
                _time.sleep(.1)
                self.window.process_events()
            
            _debug('\t Getting the voltage')
            
            # Read SIM922 data, total 56 bytes
            v22 = self.SIM922.read(nbytes=56).split(',')
            v22 = [float(i) for i in v22]
            
            self.window.process_events()
            
            # Read SIM970 data, total 45 bytes
            v70 = self.SIM970.read(nbytes=45).split(',')
            v70 = [float(i) for i in v70]
            
            self.window.process_events()
            
            # Get the time
            t = _time.time() - self.api._t0
            d['t'] = _n.append(d['t'], t)
            data   = [t]

            # Get all the voltages we're supposed to
            for n in range(4):
                if self.settings["SIM922/Channels/%d"%(n+1)]: 
                    
                    # Append the new data points
                    d['v22_'+str(n+1)] = _n.append(d['v22_'+str(n+1)], v22[n])
    
                    # Append this to the list
                    data = data + [v22[n]]
                    
                    self.window.process_events()
                    
            for n in range(4):
                if self.settings["SIM970/Channels/%d"%(n+1)]: 
                    
                    # Append the new data points
                    d['v70_'+str(n+1)] = _n.append(d['v70_'+str(n+1)], v70[n])
    
                    # Append this to the list
                    data = data + [v70[n]]
                    
                    self.window.process_events()
                    
            # Update the plot
            self.plot_raw.plot()
            self.window.process_events()

            # Write the line to the dump file
            self._dump(data)

        _debug('  Loop complete!')

        # Re-enable the connect button
        self._set_acquisition_mode(False)
        

    def _dump(self, a, mode='a'):
        """
        Opens self.path, writes the list a, closes self.path. mode is the file
        open mode.
        """
        _debug('_dump('+str(a)+', '+ repr(mode)+')')

        # Make sure everything is a string
        for n in range(len(a)): a[n] = str(a[n])
        self.a = a
        # Write it.
        f = open(self.path, mode)
        f.write(','.join(a)+'\n')
        f.close()
        
    def _set_acquisition_mode(self, mode=True):
        """
        Enables / disables the appropriate buttons, depending on the mode.
        """
        _debug('_set_acquisition_mode('+repr(mode)+')')
        self.button_connect.disable(mode)
        self.settings.disable(mode)

    def event_close(self, *a):
        """
        Quits acquisition loop when the window closes.
        """
        self.button_acquire.set_checked(False)
    
    def sim922_refresh(self):
        
        # Loop over the 4 channels
        for n in range(4):
            val = self.settings["SIM922/Channels/%d"%(n+1)]
            self.SIM922.setExcitation(n+1,val)
                
def _debug(message):
    if _DEBUG: print(message)
        
if __name__ == '__main__':
    self = SIM900()
    self.settings['VISA/Device'] = 'COM4'
    #self.button_connect.click()