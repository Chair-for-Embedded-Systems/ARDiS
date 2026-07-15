from ardis.core.scheduler import Scheduler, Application, SystemState

class GreedyScheduler(Scheduler):
    """
    A scheduler that launches the apps as soon as possible, in the order they are provided in the workload list.
    If a task order is provided, it will respect the dependencies between tasks and only launch a task when all its dependencies have completed.
    """
    
    def __init__(
        self,
        available_cores: set[int],
        task_order: dict[Application, set[Application]] | None = None
    ):
        super().__init__()
        self._available_cores = available_cores
        self._task_order = task_order

        # Check if the task_order is valid (i.e., no circular dependencies)
        if self._task_order:
            from graphlib import TopologicalSorter, CycleError
            try:
                TopologicalSorter(task_order).prepare()
            except CycleError:
                raise ValueError("The provided task_order contains circular dependencies, which is not allowed.")
                
    def register_workload(self, workload: list[Application]) -> None:
        # No precomputation needed for this simple scheduling policy
        return
    
    def is_time_to_launch(self, application: Application, system_state: SystemState) -> bool:
        """
        Check if the application can be launched based on the current system state.
        The application can be launched if there are enough available cores to accommodate it.
        """
        required_cores = application.get_preffered_core_count()
        available_cores = self._available_cores - system_state.occupied_cores
        
        # Check if enough resources are available to launch the application
        if len(available_cores) < required_cores:
            return False
        
        # Check if the application has any dependencies that need to be completed before it can be launched
        if self._task_order and application in self._task_order:
            for dependency in self._task_order[application]:
                if not dependency.is_completed():
                    return False
        
        # All checks passed, the application can be launched
        return True