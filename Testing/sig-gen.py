import visa

# Connect to the signal generator over LAN
rm = visa.ResourceManager()
sg = rm.open_resource('TCPIP::xxx.xxx.xxx.xxx::5025::SOCKET')  # Replace 'xxx.xxx.xxx.xxx' with the IP address of your signal generator

# Send SCPI commands
sg.write(':FREQ 100 MHz')  # Set the frequency to 100 MHz
sg.write(':POW -10 dBm')  # Set the output power level to -10 dBm
sg.write(':OUTP:MOD:STAT ON')  # Enable modulation
sg.write(':OUTP:MOD:TYPE AM')  # Set the modulation type to AM
sg.write(':OUTP:MOD:AM:INT:FREQ 1 kHz')  # Set the AM modulation frequency to 1 kHz
sg.write(':OUTP:MOD:AM:INT:DEPT 50%')  # Set the AM modulation depth to 50%
sg.write(':OUTP:WAV:SOUR SIN')  # Set the waveform shape to sine
sg.write(':OUTP:STAT ON')  # Enable the RF output

# Close the connection to the signal generator
sg.close()