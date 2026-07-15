from ardis.core.scheduler import Scheduler, Application, SystemState

class FixedTimeScheduler(Scheduler):
    
    def __init__(self, app_to_launchtime_seconds: dict[Application, float]):
        self.app_to_launchtime_seconds = app_to_launchtime_seconds

    def register_workload(self, workload: list[Application]):
        # Ensure that all applications in the workload have a specified launch time
        for app in workload:
            if app not in self.app_to_launchtime_seconds:
                raise ValueError(f"No launch time specified for application {app}.")

    def is_time_to_launch(self, application: Application, system_state: SystemState) -> bool:
        current_time = system_state.elapsed_time_sec
        launch_time = self.app_to_launchtime_seconds.get(application)
        if launch_time is None:
            raise ValueError(f"No launch time specified for application {application}.")
        return current_time >= launch_time