class PIDController():
    
    def __init__(self, Kp, Ki, Kd):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.prev_error = 0.0
        self.integral = 0.0
        self.desired_field = 1.0
        self.current_field = 0.0
    
    def setGains(self, Kp: float, Ki: float, Kd: float):
        print(f"PID gains set to: Kp = {Kp}, Ki = {Ki}, Kd = {Kd}")
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
    
    def setTargetValue(self, setpoint: float):
        self.desired_field = setpoint
        print(f"Desired floor at: {setpoint}, Target field at: {self.desired_field}")
        
    def getTargetValue(self) -> float:
        return self.desired_field
    
    def calculate(self, current_field: float) -> float:
        error = self.desired_field - current_field
        self.integral += error
        derivative = error - self.prev_error
        output = (self.Kp * error) + (self.Ki * self.integral) + (self.Kd * derivative)
        self.prev_error = error
        print(f"Current Field: {current_field}, Error: {error}, Integral: {self.integral}, Derivative: {derivative}, Output: {output}")
        return output
    
    def clear(self):
        self.measured_value = 0.0
        self.prev_error = 0.0
        self.integral = 0.0