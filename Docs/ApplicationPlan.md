Features:
1. Desired Field Intensity/Amplitude Input (V/m)
    a. Input Field w Up/Down Buttons: 
2. Current Field Intensity Display:
    a. Liveview (X, Y, Z Color Plot)
    b. V/m Plot Over Time
    c. Numbers
3. Current Signal Generator Output:
    a. Power Level Slider
    b. dBm Over Time Graph
    c. Frequency Over Time Graph
4. Signal Generator Settngs:
    a. Frequency Sweep
    b. AM Modulation On
    b. AM Modulation Frequency
    c. AM Modulation Depth

Sig-Gen LAN Settings:
IP Address: 192.168.80.79 (was 192.168.80.87)
Gateway: 192.168.80.100 (was 192.168.80.100)
Port: 5024

Freq 250 kHz to 6 GHz
Power -110 dBm to 14 dBm

Use :FREQ and :POW and :OUTP:STAT ON
:AM:DEPT:LIN 30
:AM:STAT ON
:AM:STAT?

sigGen = socketscpi.SocketInstrument('192.168.100.79')

sigGen.query('*IDN?')


ETS Lindgren DLL Family Strings:
HI-Any HI-6005 MS HI-6005 HS HI-6005
 Baud rates are at 9600 and 115.2 K for the laser models

Communication Protocol:

Data Type: RS-232 Serial
Data Mode: Asynchronous
Word Length: 7-bit
Parity: Odd
Stop Bits: 1
Rate: 9600 Baud

Information Transfer Protocol: 
Command responses:
":" + Command Letter + Data + <CR>

Commands:
D3: Read Probe Data
Response: :Dx.xxxyy.yyzzz.zB<CR> (B is battery flag)

D5: Read probe data (include compositer field)
Response: :Dx.xxxyy.yyzzz.zcccc.B<CR>

Application Architecture:
Main Window:
DataReceived:
SetSiggen

FieldProbe: QObject
StartProbe:
DataRecevied:
StopProbe:
HI-60XX-Serial: serial

SignalGenerator: QObject
Connect:
SetSweep:
Set AM Modulation(Freq, Depth):
SetPower:
Start:
Stop:
AgilentSCPI: socket, socketscpi, visa



### -------------Oct 15---------------

Unit Pictures
Plots not showing
Allow spin boxes to go neg
Modulation label buttons are off (freq not heard, Mode doesn't chnage % - dBm)
All radio buttons don't intiate with one picked
Not all radio buttons disabled when its time (FM mod mode buttons)
PM button not togglable.
Sweep still not implemented.
Device pictures needed.
Signal modulation UI unresponsive.
Pow and Freq run 3 times...
Cleanup threads with SIGINT

## Todo

- Plots not showing
- ?? Not all radio buttons disabled when its time (FM mod mode buttons)
- Sweep still not implemented.
- Signal modulation UI unresponsive.
- Pow and Freq run 3 times...
- Cleanup threads with SIGINT
- Only start discovery threads once UI is setup
- Other widgets
- Sweep arguments dno't come through. 
- Mod types don't gull change choice UI.
- methods are not connected
- sweep bar should start hidden
- RF On with sweep has no states to pass.


## Done

- PM button not togglable.
- freq not heard
- Modulation label buttons are off (, Mode doesn't chnage % - dBm)
- Allow spin boxes to go neg
- Unit Pictures
- Missing: X, Y, Z field inesities:, Probe Temp, Charge
- PM, AM FM, control abilities;
- Linear, Exp Sweep
- Internal, External Mod Coupling/Source
- All radio buttons don't intiate with one picked
- Device pictures needed.
