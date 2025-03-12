#!/usr/bin/env python3
"""
Equipment Limits Module
=======================
This module defines the EquipmentLimits class which is used to manage equipment
limits such as frequency ranges for the antenna and amplifier, along with the maximum
power limit. The class provides methods to set and retrieve these limits, making it
useful in systems where equipment operating parameters must be validated.
"""
class EquipmentLimits():
    """
    EquipmentLimits class manages frequency and power limits for equipment components.
    
    Attributes:
        ant_min_freq (float): Minimum frequency limit for the antenna.
        amp_min_freq (float): Minimum frequency limit for the amplifier.
        ant_max_freq (float): Maximum frequency limit for the antenna.
        amp_max_freq (float): Maximum frequency limit for the amplifier.
        max_power (float): Maximum allowed power.
    """
    
    def __init__(self, ant_min_freq: float, amp_min_freq: float, ant_max_freq: float, amp_max_freq: float, max_power: float):
        """
        Initialize the EquipmentLimits instance with specified frequency and power parameters.

        Parameters:
            ant_min_freq (float): The minimum frequency limit for the antenna.
            amp_min_freq (float): The minimum frequency limit for the amplifier.
            ant_max_freq (float): The maximum frequency limit for the antenna.
            amp_max_freq (float): The maximum frequency limit for the amplifier.
            max_power (float): The maximum allowed power.
        """
        self.ant_min_freq = ant_min_freq
        self.amp_min_freq = amp_min_freq
        self.ant_max_freq = ant_max_freq
        self.amp_max_freq = amp_max_freq
        self.max_power = max_power

    def setAntennaMinFrequency(self, freq: float):
        """
        Set the minimum frequency limit for the antenna.

        Parameters:
            freq (float): The new minimum frequency for the antenna.
        """
        self.ant_min_freq = freq
        
    def setAmplifierMinFrequency(self, freq: float):
        """
        Set the minimum frequency limit for the amplifier.

        Parameters:
            freq (float): The new minimum frequency for the amplifier.
        """
        self.amp_min_freq = freq
        
    def setAntennaMaxFrequency(self, freq: float):
        """
        Set the maximum frequency limit for the antenna.

        Parameters:
            freq (float): The new maximum frequency for the antenna.
        """
        self.ant_max_freq = freq
        
    def setAmplifierMaxFrequency(self, freq: float):
        """
        Set the maximum frequency limit for the amplifier.

        Parameters:
            freq (float): The new maximum frequency for the amplifier.
        """
        self.amp_max_freq = freq

    def setMaxPower(self, power: float):
        """
        Set the maximum allowed power.

        Parameters:
            power (float): The new maximum power value.
        """
        self.max_power = power
        
    def getMinFrequency(self):
        """
        Retrieve the effective minimum frequency by comparing the antenna and amplifier minimum frequencies.

        Returns:
            float: The higher value between the antenna's and amplifier's minimum frequencies.
        """
        return max(self.ant_min_freq, self.amp_min_freq)
    
    def getMaxFrequency(self):
        """
        Retrieve the effective maximum frequency by comparing the antenna and amplifier maximum frequencies.

        Returns:
            float: The lower value between the antenna's and amplifier's maximum frequencies.
        """
        return min(self.ant_max_freq, self.amp_max_freq)
    
    def getMaxPower(self):
        """
        Retrieve the maximum allowed power.

        Returns:
            float: The maximum power value.
        """
        return self.max_power