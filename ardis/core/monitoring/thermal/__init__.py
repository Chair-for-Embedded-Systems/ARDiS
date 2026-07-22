from .factory import create_core_temp_monitor
from .thermal_monitor import CoreTemperatureMonitor

__all__ = [
    "create_core_temp_monitor",
    "CoreTemperatureMonitor",
]