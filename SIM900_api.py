"""
Written by Brandon Ruffolo for the Modern Physics lab at McGill University.
"""

import numpy   as _n
import time    as _time
import pyvisa  as _visa

_DEBUG      = True
_AUTO_FLUSH = True
WRITE_DELAY = .3

class SIM900_api():
    """
    This object lets you query the SRS SIM900 Mainframe.


    Parameters
    ----------
    name='ASRL3::INSTR'
        Visa resource name. Use R&S Tester 64-bit or NI-MAX to find this.

    pyvisa_py=False
        If True, use the all-python VISA implementation. On Windows, the simplest
        Visa implementation seems to be Rhode & Schwarz (streamlined) or NI-VISA (bloaty),
        with pyvisa_py=False.

    """

    def __init__(self, name='ASRL4::INSTR', pyvisa_py=False):

        # Create a resource management object
        self.resource_manager = _visa.ResourceManager()
        
        self.id = None

        # Get time t=t0
        self._t0 = _time.time()

        # Try to open the instrument.
        try:
            self.instrument = self.resource_manager.open_resource(name)
            self.instrument.timeout = 2000

            # Test that it's responding and figure out the type.
            try:
                # Flush all port buffers, in case old data is present
                self.instrument.write("FLSH")

                # Ask for the model identifier
                self.id = self.query('*IDN?').replace(",", " ")
                print("ID: %s"%self.id)
                
            except:
                print("ERROR: Instrument did not reply to ID query. Entering simulation mode.")
                self.instrument.close()
                self.instrument = None

        except:
            self.instrument = None
            if self.resource_manager:
                print("ERROR: Could not open instrument. Entering simulation mode.")
                print("Available Instruments:")
                for name in self.resource_manager.list_resources(): print("  "+name)
        
        
    def write(self, message):
        """
        Writes the supplied message.

        Parameters
        ----------
        message
            String message to send to the mainframe.
        """
        _debug('write('+"'"+message+"'"+')')

        if self.instrument == None: s = None
        else:                       s = self.instrument.write(message)

        return s

    
    def read(self):
        """
        Reads a message from the mainframe output buffer.
        
        Returns
        -------
        str
            Data from the mainframe.
        
        """
        _debug('read()')


        if self.instrument == None: response = ''
        else:                       response = self.instrument.read()

        _debug('  '+repr(response))
        return response.strip()
    
    def query(self, message):
        """
        Writes the supplied message and reads the response.
        """
        #_debug("query('"+message+"')")

        self.write(message)
        _time.sleep(WRITE_DELAY)
        
        response = self.read()
        return response.strip()
    
    def writePort(self, port, message):
        """
        Writes a message to the selected port.

        Parameters
        ----------
        port (int)
            Port number (between 1-8) to be addressed.
            
        message (str)
            String message to send to the mainframe.
            
        """        
        _debug('writePort('+"'"+message+"'"+')')
        self.instrument.write("SNDT %d, '%s'"%(port,message))
    
    def readPort(self, port, nbytes = None):
        """
        Reads a message from the selected port buffer.

        Parameters
        ----------
        port (int)
            Port number (between 1-8) to be addressed.
            
        nbytes(int)
            (Optional) Number of bytes to retrieve from port.
            If not supplied, mainframe will be queried to 
            determine it's value.
        
        """     
        # Determine number of bytes waiting in the port input buffer
        if (nbytes == None): nbytes = self.inWaiting(port)
        
        # Request nbytes from port 
        self.instrument.write("RAWN? %d,%d" %(port,nbytes))
        
        # Wait for bytes to arrive in the host queue
        _time.sleep(WRITE_DELAY)
        
        # Read the response
        response = self.read()
        
        return response
    
    def queryPort(self, port, message, nbytes = None):
        """
        Queries the selected port.
        Automatically flushes the port before query.

        Parameters
        ----------
        port (int)
            Port number (between 1-8) to be addressed.
            
        message (str)
            String message to send to the mainframe.
            
        nbytes(int)
            (Optional) Number of bytes to retrieve from port.
            If not supplied, mainframe will be queried to 
            determine it's value.
            
        Returns
        -------
        str
            Query response from the selected port.
        
        """   
        
        if(_AUTO_FLUSH):
            # Pre-emptively flush the port 
            self.flush(port)
        else:
            # Check port for pre-existing data, flush if there is
            if(self.inWaiting(port) != 0): self.flush(port)
        
        # Write message to port
        self.writePort(port,message)
        
        _time.sleep(WRITE_DELAY)
        
        # Read port
        s = self.readPort(port)
        return s

    def inWaiting(self, port):
        """
        Queries the mainframe to get the number of bytes waiting
        in the selected port input buffer.

        Parameters
        ----------
        port : int
            Port number (between 1-8) to be addressed.

        Returns
        -------
        int
            Number of bytes waiting in the selectedport input buffer.

        """
        n = self.query("NINP? %d"%port)
        
        return int(n)
        
    def flush(self, port = None):
        """
        Flushes Port input buffers [associated with the selected port].
        If no port number is supplied, all port buffers are flushed.

        Parameters
        ----------
        port : int (optional)
            Port number to flush.

        """
        if(port==None): self.instrument.write("FLSI")
        else:           self.instrument.write("FLSI %d"%port)
        
    def scanPorts(self, verbose = False):
        """
        Scan all ports for connected modules.
        
        verbose : bool
            If True, print a list of the port contents.

        Returns
        -------
        List
            A 8-element list. Each element is either a string 
            of the module ID or a None. 

        """
    # Loop over all port numbers
        ports = []
        for i in range(1,9):
            
            self.instrument.write("SNDT %d,'*IDN?'"%i)
            _time.sleep(.1)
            j = self.inWaiting(i)
            if(j!= 0): 
                s = self.query("RAWN? %d,%d"%(i,j)).split(',')[1]          
                if(verbose): print("Port %d: %s"%(i,s))
                ports.append(s)
            else:
                if(verbose): print("Port %d: Empty"%i)
                ports.append(None)
        return ports
    
    def close(self):
        """
        Closes the connection to the device.
        
        """
        _debug("close()")
        if not self.instrument == None: self.instrument.close()        





    class SIM_Module():
        """
        General SIM module object.
        
        Parameters
        ----------
        SIM900_api
            The SRS SIM900 Mainframe API object that the Module is 
            connected to.
            
        port (int)
            Port number (between 1-8) of the Module to be addressed.
        
        """  
        def __init__(self, SIM900_api, port):
            self.SIM900 = SIM900_api
            self.port = port
            
            # Query the module for it's ID
            self.id = self.query("*IDN?")[33:].replace(",", " ")
        
        def write(self, msg):
            """
            Writes a message to the SIM module.

            Parameters
            ----------
                
            message (str)
                String message to send to the module.
                
            """   
            self.SIM900.writePort(int(self.port),msg)
        
        def read(self, nbytes = None):
            """
            Reads a message from the selected SIM module port buffer.

            Parameters
            ----------
            nbytes(int)
                (Optional) Number of bytes to retrieve from port.
                If not supplied, mainframe will be queried to 
                determine it's value.
            
            """     
            return self.SIM900.readPort(self.port, nbytes)
        
        def query(self, msg, nbytes = None):
            """
            Queries the module.
            Automatically flushes the module before query.
    
            Parameters
            ----------
            message (str)
                String message to send to the module.
            nbytes(int)
                (Optional) Number of bytes to retrieve from module.
                If not supplied, mainframe port buffer will be queried to 
                determine it's value.
                
            Returns
            -------
            str
                Query response from the module.
            
            """      
            return self.SIM900.queryPort(self.port, msg)     
            
        def getID(self):
            return self.id        
        
        
        
    class SIM922_api(SIM_Module):
        """
        This object lets you query an SRS 922 Diode Temperature Monitor
        Module.
        
        Parameters
        ----------
        SIM900_api
            The SRS SIM900 Mainframe API object that the SIM922 is 
            connected to.
        port (int)
            Port number (between 1-8) of the SIM922 to be addressed.
        
        """
        def __init__(self, SIM900_api, port):
            super().__init__(SIM900_api, port)
            return 
        
        def getExcitation(self, channel = None):
            """
            Get excitation state (current ON/OFF) on a given channel.
            
            Parameters
            ----------
            channel (int)
                (Optional) Channel number (between 1-4) to be queried.
                If no argument is given, then all four excitation states
                are read. 
                
            Returns
            -------
            bool
                Excitation state of requested channel.
                If no channel number was supplied, a list 
                of all four excitation states is returned.
            
            """
            if channel == None:
                ex = self.SIM900.queryPort(self.port,"EXON? 0")
                
                # Format the response into boolean array
                ex = ex.replace(' ','').split(',')
                
                return [bool(int(e)) for e in ex]
            else:
                ex = self.SIM900.queryPort(self.port,"EXON? %d"%channel)
                return bool(int(ex))
        
        def setExcitation(self, channel, state):
            """
            

            Parameters
            ----------
            channel : TYPE
                DESCRIPTION.
            state : TYPE
                DESCRIPTION.

            Returns
            -------
            None.

            """
            self.write("EXON %d, %d"%(channel,state))
    class SIM970_api(SIM_Module):
        """
        This object lets you query an SRS 970 Quad Digital Voltmeter
        Module.
        
        Parameters
        ----------
        SIM900_api
            The SRS SIM900 Mainframe API object that the SIM970 is 
            connected to.
            
        port (int)
            Port number (between 1-8) of the SIM970 to be addressed.
        
        """        
        def __init__(self, SIM900_api, port):
            super().__init__(SIM900_api, port) 
        
        def funMesg(self):
            self.write("DISX 3 ,0")
            self.write("DISX 4 ,0")
            
            #_time.sleep(.1)
            
            self.write("MESG 3 ,_CRYO")
            self.write("MESG 4 ,_STAT")
            

def _debug(message):
    if _DEBUG: print(message)
    
if __name__ == '__main__':
    self = SIM900_api('ASRL4::INSTR')
    
    # Setup a SIM922 on port 1
    SIM922 = self.SIM922_api(self, 1)
    
    # Setup a SIM970 on port 7
    SIM970 = self.SIM970_api(self, 7)