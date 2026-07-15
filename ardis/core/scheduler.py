#class Scheduler:
#    def __init__(self):
#        # schedule is a dictionary with the application as key and the time of arrival as value
#        self.schedule = {}
#    
#    # Create a schedule for the applications
#    def createSchedule(self, applications):
#        # default schedule: all applications arrive at the same time
#        for app in applications:
#            self.schedule[app] = 0
 #   # Check if it is time to launch an application
#    def isTimeToLaunch(self, app, current_time):
#        return current_time >= self.schedule[app]

from abc import ABC, abstractmethod
from ardis.benchmarks.application import Application
from ardis.core.system_state import SystemState

class Scheduler(ABC):

    @abstractmethod
    def register_workload(self, workload: list[Application]):
        """
        This method is called by the engine before the workload is executed.
        It allows the scheduler to prepare for the workload, e.g., by precomputing a schedule or validating its parameters.
        """
        raise NotImplementedError("Subclasses must implement this method.")

    @abstractmethod
    def is_time_to_launch(self, application: Application, system_state: SystemState) -> bool:
        raise NotImplementedError("Subclasses must implement this method.")
    
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