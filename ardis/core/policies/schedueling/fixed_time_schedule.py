from ardis.core.scheduler import Scheduler, Application, SystemState

class FixedTimeScheduler(Scheduler):
    """
    A scheduler that launches applications at predefined times.
    The launch times are specified in seconds relative to the start of the workload.
    All applications must have a specified launch time in the provided dictionary.
    """
    def __init__(self, app_to_launchtime: dict[Application, float]):
        """
        Initializes the FixedTimeScheduler with a mapping of applications to their launch times.
        
        Parameters:
            - app_to_launchtime_seconds: Dictionary mapping each `Application` to its launch time in seconds.
        """
        self.app_to_launchtime_seconds = app_to_launchtime

    def register_workload(self, workload: list[Application]):
        # Validate that all applications in the workload have a specified launch time
        for app in workload:
            if app not in self.app_to_launchtime_seconds:
                raise ValueError(f"No launch time specified for application {app}.")

    def is_time_to_launch(self, application: Application, system_state: SystemState) -> bool:
        current_time = system_state.elapsed_time_sec
        launch_time = self.app_to_launchtime_seconds.get(application)
        if launch_time is None:
            raise ValueError(f"No launch time specified for application {application}.")
        return current_time >= launch_time