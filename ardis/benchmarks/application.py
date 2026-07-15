from abc import ABC, abstractmethod

class Application(ABC):
    __INSTANCE_COUNTER: int = 0
    def __init__(self, labels: list[str]) -> None:
        """
        Parameters
        ----------
        labels: list[str]
            List of arbitrary labels that can be used for different purposes. E.g. marking for later use in a policy
        """
        super().__init__()
        self._labels: list[str] = labels
        self._running: bool = False
        self._pid: int | None = None
        self._start_affinity: set[int] | None = None
        self._instance_id: int = Application.__INSTANCE_COUNTER
        Application.__INSTANCE_COUNTER += 1

    def execute(self, cores: set[int] | None):
        """
        Starts the execution of the application and blocks until it has finished.
        This method is a wrapper for `_execute`, which actually executes the application
        """
        if not self._running:
            self._running = True
            self._start_affinity = cores
            self._execute(cores)
            self._running = False
            self._pid = None

    @abstractmethod
    def _execute(self, cores: set[int] | None) -> None:
        """
        Starts the execution of the application and blocks until it has finished.
        """
        raise NotImplementedError

    @abstractmethod
    def terminate(self) -> None:
        """
        Terminates the application if it is running.
        """
        raise NotImplementedError

    @abstractmethod
    def get_pid(self) -> int | None:
        """
        Returns the PID of this application,
        may return None if the pid could not be determined.
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_display_name(self) -> str:
        """
        Returns the display name for the application.
        This is the name that will be used in the log files
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_preffered_core_count(self) -> int:
        """
        Returns the number of cores that this application prefers to run on.
        """
        raise NotImplementedError
    
    def get_labels(self) -> list[str]:
        """
        Returns the labels that are assigned to this application
        """
        return self._labels
    
    def get_instance_id(self) -> int:
        """
        Returns the instance id of this application.
        This is a unique id that is assigned to each instance of an application.
        """
        return self._instance_id

    def __str__(self) -> str:
        return self.get_display_name()