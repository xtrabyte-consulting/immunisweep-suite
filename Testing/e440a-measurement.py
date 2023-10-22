import visa
import numpy as np
import matplotlib.pyplot as plt

# Connect to the spectrum analyzer over LAN
rm = visa.ResourceManager()
sa = rm.open_resource('TCPIP::192.168.1.77::5025::SOCKET')

# Identify the instrument
print(sa.query('*IDN?'))

# Set up the measurement parameters
sa.write('INIT:CONT OFF') # Disable continuous measurement
sa.write('FREQ:STAR 100 MHz') # Set the start frequency to 100 MHz
sa.write('FREQ:STOP 1 GHz') # Set the stop frequency to 1 GHz
sa.write('BAND:RES 10 kHz') # Set the resolution bandwidth to 10 kHz
sa.write('BAND:VID 100 kHz') # Set the video bandwidth to 100 kHz
sa.write('DISP:TRAC:Y:RLEV 0 dBm') # Set the reference level to 0 dBm
sa.write('CALC:MARK1:MAX') # Find and set the marker to the maximum signal level
sa.write('CALC:MARK1:Y?') # Query the Y-axis value of the marker

# Perform the measurement and receive trace data
sa.write('INIT:IMM') # Start the measurement
sa.query('*OPC?') # Wait for the measurement to complete
trace_data = sa.query_ascii_values('TRAC:DATA? TRACE1') # Receive trace data
freq_data = np.linspace(float(sa.query('FREQ:STAR?')), float(sa.query('FREQ:STOP?')), len(trace_data)) # Create frequency data

# Display the trace data
plt.plot(freq_data/1e9, trace_data)
plt.xlabel('Frequency (GHz)')
plt.ylabel('Amplitude (dBm)')
plt.title('Spectrum Analyzer Trace Data')
plt.show()

# Close the connection to the instrument
sa.close()