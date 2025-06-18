from abc import ABC, abstractmethod

class Application(ABC):
    def __init__(self, labels: list[str]) -> None:
        super().__init__()
        self._labels = labels
        self._running = False

    def execute(self, cores: set[int] | None):
        """
        Starts the execution of the application and blocks until it has finished.
        This method is a wrapper for `_execute`, which actually executes the application
        """
        if not self._running:
            self._running = True
            self._execute(cores)
            self._running = False

    @abstractmethod
    def _execute(self, cores: set[int] | None) -> None:
        """
        Starts the execution of the application and blocks until it has finished.
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
    
    def get_labels(self) -> list[str]:
        return self._labels
    
    def __str__(self) -> str:
        return self.get_display_name()