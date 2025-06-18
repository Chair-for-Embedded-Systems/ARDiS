from abc import ABC, abstractmethod

class Application(ABC):
    def __init__(self) -> None:
        super().__init__()

    @abstractmethod
    def execute(self, cores: set[int] | None) -> None:
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
    
    def __str__(self) -> str:
        return self.get_display_name()