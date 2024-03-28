# Signal Generator Auto-Frequency Sweep and Closed-Loop Power Controller Desktop Application

## Desktop application that utilizes the PyQt framework and custom SCPI and serial drivers to run linear and exponential frequency sweeps on an extra-wide-band (2kHz - 6GHz) RF Signal Generator while keeping the electromagnetic field at a constant amplitude via closed-loop control from field probe feedback input

### FieldIntensityController.py

- Root of the application: Sets up UI, connects UI actions with hardware control and information feedback from device drivers via Signals and Slots. Also runs the PID loop for steady-state field control via the Signal Generator's output.

### FieldProbe.py

- File for all supported Field Probes at the moment with the aim to make the interface as modular as possible with the controller
- Contains some objects for software testing without hardware-in-the-loop and the **ETSLindgrenHI6006** class for use with the customer's onsite hardware, with a custom dynamic serial reading protocol on a separate thread that reads exact string lengths to avoid any application lag given serial's large over head especially in Python

### SignalGinerator.py

- File containing both a test Signal Generator class for pure software testing as well as the **AgilentN5181A** object. In this class, the modulation type, power, and state of the signal is set, and the frequency sweep functions are run here as well. The **AgilentN5181A** object uses SCPI over ethernet to command the current frequency, power, modulation scheme, etc.,.

### MainWindow.py

- Autogenerated from the XML file created by Qt Designer

### Plots.py

- Work in progress to show the frequency sweep and power control on the UI Dashboard

### Resources.qrc/py

- UI Asset resource files for bundling application across Operating Systems.
