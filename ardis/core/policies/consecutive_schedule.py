from ardis.core.scheduler import Scheduler, Application

class ConsecutiveScheduler(Scheduler):
    def __init__(self, delay_sec: float):
        super().__init__()
        self._delay = delay_sec
        self._schedule : dict[Application, float] = {}
    
    def register_workload(self, workload: list[Application]) -> None:
        relative_start_time_sec = 0
        for app in workload:
            self._schedule[app] = relative_start_time_sec
            relative_start_time_sec += self._delay

    def is_time_to_launch(self, application: Application, system_state) -> bool:
        """
        Check if the application is scheduled to start based on the current system time.
        """
        if application not in self._schedule:
            raise ValueError(f"Application {application} not found in schedule.")
        
        scheduled_time = self._schedule[application]
        current_time = system_state.elapsed_time_sec
        
        return current_time >= scheduled_time