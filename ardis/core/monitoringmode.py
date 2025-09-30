from enum import Enum

class MonitoringMode(Enum):
    
    """
    Enum class for monitoring mode
    """
    OFF = 0
    PERIODIC_ON_CORE = 1
    PERIODIC_ON_PID = 2
    PERIODIC_ON_TID = 3