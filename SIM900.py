"""
Written by Brandon Ruffolo for the Modern Physics lab at McGill University.
"""

import numpy   as _n
import time    as _time
import pyvisa  as _visa

_DEBUG = False
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
                self.id = self.query('*IDN?')
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
            String message to send to the DMM.
        """
        _debug('write('+"'"+message+"'"+')')

        if self.instrument == None: s = None
        else:                       s = self.instrument.write(message)

        return s

    
    def read(self):
        """
        Reads a message and returns it.

        Parameters
        ----------
        process_events=False
            Optional function to be called in between communications, e.g., to
            update a gui.
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
        _debug("query('"+message+"')")

        self.write(message)
        _time.sleep(WRITE_DELAY)
        
        response = self.instrument.read()
        return response.strip()
    
    def writePort(self, port, message):
        self.instrument.write("SNDT %d, '%s'"%(port,message))
    
    def readPort(self, port, nbytes = None):
        
        # Determine number of bytes waiting in the port input buffer
        if (nbytes == None): nbytes = self.inWaiting(port)
        
        self.instrument.write("RAWN? %d,%d" %(port,nbytes))
        _time.sleep(WRITE_DELAY)
        response = self.instrument.read()
        
        return response.strip()
    
    def queryPort(self, port, message, nbytes = None):
        
        if(self.inWaiting(port) != 0): self.flush(port)
        self.writePort(port,message)
        _time.sleep(WRITE_DELAY)
        s = self.readPort(port)
        return s

    def inWaiting(self, p):
        """
        Queries the mainframe to get the number of bytes waiting
        in the Port p input buffer.

        Parameters
        ----------
        p : int
            Port number 1-8.

        Returns
        -------
        int
            Number of bytes waiting in port p input buffer.

        """
        n = self.query("NINP? %d"%p)
        
        return int(n)
        
    def flush(self, port = None):
        """
        Flushes Port input buffers [associated with port p].

        Parameters
        ----------
        p : int (optional)
            Port number to flush.

        """
        if(port==None): self.instrument.write("FLSI")
        else:           self.instrument.write("FLSI %d"%port)
        
    def scanPorts(self):
    # Loop over all port numbers
        for i in range(1,9):
            
            self.instrument.write("SNDT %d,'*IDN?'"%i)
            _time.sleep(.1)
            j = self.inWaiting(i)
            if(j!= 0): 
                s = self.query("RAWN? %d,%d"%(i,j)).split(',')[1]          
                print("Port %d: %s"%(i,s))
            else:
                print("Port %d: Empty"%i)

def _debug(message):
    if _DEBUG: print(message)
    
if __name__ == '__main__':
    self = SIM900_api()