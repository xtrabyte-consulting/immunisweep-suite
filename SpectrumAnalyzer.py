import time
import socket

class HPE4440A:
    def __init__(self, ip, port=5025, timeout=2):
        """
        Initialize the Spectrum Analyzer connection.
        
        :param ip: IP address of the spectrum analyzer.
        :param port: TCP port (default 5025, common for SCPI instruments).
        :param timeout: Socket timeout in seconds.
        """
        self.ip = ip
        self.port = port
        self.timeout = timeout
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        self.socket.connect((ip, port))
        # Give the instrument a moment to be ready.
        time.sleep(0.2)
    
    def send_command(self, command):
        """
        Send a SCPI command (without waiting for a response).
        
        :param command: A string containing the SCPI command.
        """
        full_command = command + "\n"
        self.socket.sendall(full_command.encode('ascii'))
    
    def query(self, command, buffer_size=1024):
        """
        Send a SCPI query and return the response.
        
        :param command: A string containing the SCPI query.
        :param buffer_size: The maximum number of bytes to read.
        :return: The response string.
        """
        self.send_command(command)
        # A short delay may be necessary for the instrument to respond.
        time.sleep(0.1)
        data = self.socket.recv(buffer_size)
        return data.decode('ascii').strip()
    
    def set_window(self, start_freq, stop_freq):
        """
        Set the analyzer frequency window.
        
        According to the Keysight E4440A manual, the frequency range is set with:
            FREQ:STAR <start frequency in Hz>
            FREQ:STOP <stop frequency in Hz>
        
        :param start_freq: Start frequency in Hz.
        :param stop_freq: Stop frequency in Hz.
        """
        self.send_command(f"FREQ:STAR {start_freq}")
        self.send_command(f"FREQ:STOP {stop_freq}")
        # Allow time for the instrument to update.
        time.sleep(0.1)
    
    def set_units(self, units):
        """
        Set the measurement/display units on the analyzer.
        
        For example, to display in voltage rather than power, many Keysight instruments
        support the UNIT:POW command. In this example we assume:
            UNIT:POW VOLT  --> to display voltage
            UNIT:POW DBM   --> to display power in dBm
            
        Consult your manual for the correct command.
        
        :param units: A string specifying the units ('V' or 'DBM').
        """
        unit = units.upper()
        if unit not in ("V", "DBM", "DBMV", "DBUV", "W"):
            raise ValueError("Unsupported unit. Use 'V', 'DBMV', 'DBUV', 'W' or 'DBM'.")
        self.send_command(f"UNIT:POW {unit}")
        time.sleep(0.1)
        
    def set_marker_at_frequency(self, frequency):
        """
        Set the analyzer center frequency to the specified value and place marker 1 at that frequency.
        
        The sequence of commands is based on typical Keysight procedures:
            - Set the center frequency.
            - Activate Marker 1.
        
        :param frequency: Frequency (in Hz) at which to place the marker.
        """
        # Set center frequency
        self.send_command(f"FREQ:CENT {frequency}")
        time.sleep(0.1)
        
        # Activate Marker 1 at the center
        self.send_command("CALC:MARK1:MODE POS")
        time.sleep(0.1)
    
    def read_voltage(self, frequency):
        """
        Return the measured amplitude (voltage) at the current marker frequency position.
        
        The sequence of commands is based on typical Keysight procedures:
            - Set the center frequency.
            - Activate Marker 1.
            - Optionally, perform a peak search.
            - Query the marker amplitude with CALC:MARK1:Y?
        
        :param frequency: Frequency (in Hz) at which to read the voltage.
        :return: The measured voltage (float), or None if the read fails.
        """
        # Query the marker amplitude.
        response = self.query("CALC:MARK1:Y?")
        try:
            voltage = float(response)
            return voltage
        except ValueError:
            print(f"Failed to convert response '{response}' to float.")
            return None

    def close(self):
        """
        Close the connection to the spectrum analyzer.
        """
        self.socket.close()