class EquipmentLimits():
    
    def __init__(self, ant_min_freq: float, amp_min_freq: float, ant_max_freq: float, amp_max_freq: float, max_power: float):
        self.ant_min_freq = ant_min_freq
        self.amp_min_freq = amp_min_freq
        self.ant_max_freq = ant_max_freq
        self.amp_max_freq = amp_max_freq
        self.max_power = max_power

    def setAntennaMinFrequency(self, freq: float):
        self.ant_min_freq = freq
        
    def setAmplifierMinFrequency(self, freq: float):
        self.amp_min_freq = freq
        
    def setAntennaMaxFrequency(self, freq: float):
        self.ant_max_freq = freq
        
    def setAmplifierMaxFrequency(self, freq: float):
        self.amp_max_freq = freq

    def setMaxPower(self, power: float):
        self.max_power = power
        
    def getMinFrequency(self):
        return max(self.ant_min_freq, self.amp_min_freq)
    
    def getMaxFrequency(self):
        return min(self.ant_max_freq, self.amp_max_freq)
    
    def getMaxPower(self):
        return self.max_power