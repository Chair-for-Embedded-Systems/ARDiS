from ardis.core.scheduler import Scheduler, Application, SystemState

class ConsecutiveScheduler(Scheduler):
    """
    A scheduler that launches the applications in the order they are provided in the workload list, with a fixed delay between each launch.
    It does not consider the available resources (cpu_cores), so a subsequent `MappingPolicy` might throw an `MappingException`.
    """

    def __init__(self, delay_sec: float):
        super().__init__()
        self._delay = delay_sec
        self._schedule : dict[Application, float] = {}
    
    def register_workload(self, workload: list[Application]) -> None:
        relative_start_time_sec = 0
        for app in workload:
            self._schedule[app] = relative_start_time_sec
            relative_start_time_sec += self._delay

    def is_time_to_launch(self, application: Application, system_state: SystemState) -> bool:
        """
        Check if the application is scheduled to start based on the current system time.
        """
        if application not in self._schedule:
            raise ValueError(f"Application {application} not found in schedule.")
        
        scheduled_time = self._schedule[application]
        current_time = system_state.elapsed_time_sec
        
        return current_time >= scheduled_time