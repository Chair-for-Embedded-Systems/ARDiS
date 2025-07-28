from abc import abstractmethod
from threading import Lock
from benchmarks.application import Application

class EventBuffer:

    @abstractmethod
    def push_core_and_sys_events(self,
                        app_events: dict[int, dict[str, int|float]],
                        system_events: dict[str, int|float],
                        frequencies: dict[int, float]
                        ) -> None:
        """Adds the given core and system events to the buffer."""
        raise NotImplementedError

    @abstractmethod
    def push_pid_and_sys_events(
        self,
        app_events: dict[int, dict[str, int|float]],
        system_events: dict[str, int|float],
        frequencies: dict[int, float],
        relative_sample_time: float,
        pid_to_application: dict[int, Application]
    ) -> None:
        """Adds the given pid and system events to the buffer."""
        raise NotImplementedError

    @abstractmethod
    def get_metrics_for_core(self, core_id: int, n: int) -> list[dict[str, int|float]]:
        """
        Returns the last `n` metrics for the given `core_id` as list,
        where the **first** element in the list is the **oldest**.
        
        Returns an empty list if there are no metrics for the given `core_id` in the buffer.

        Example:
        >>> get_metrics_for_core(core=12, n=2)
        [
            {"instructions": 100, "cycles": 20, ... },
            {"instructions": 110, "cycles": 25, ... }
        ]
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_metrics_for_pid(self, pid: int, n: int) -> list[dict[str, int|float]]:
        """
        Returns the last `n` metrics for the given `pid` as list,
        where the **first** element in the list is the **oldest**.

        Returns an empty list if there are no metrics for the given `pid` in the buffer.

        Example:
        >>> get_metrics_for_pid(pid=42, n=2)
        [
            {"instructions": 100, "cycles": 20, ... },
            {"instructions": 110, "cycles": 25, ... }
        ]
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_system_metrics(self, n: int) -> list[dict[str, int|float]]:
        """
        Returns the last `n` system events as list, 
        where the **first** element in the list is the **oldest**.

        The keys in the dict correspond to those in `config.periodic_system_wide_events`
        
        Example: 
        >>> get_system_metrics(n=2)
        [
          {"power/energy-pkg/": 10, "power/energy-cores/": 2, ...}
          {"power/energy-pkg/": 12, "power/energy-cores/": 3, ...}
        ]
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_metrics_by_core(self, n: int) -> list[dict[int, dict[str, float|int]]]:
        """
        Returns the last `n` metrics for all applications as list of dict,
        where the **first** element in the list is the **oldest**.

        Example:
        >>> get_metrics_by_core(n=2)
        [
          {
            2: {"instructions": 100, "cycles": 20, ... },
            16: { "instructions": 200, "cycles": 40, ...  }
          },
          {
            2: { ... },
            16: { ... }
          }
        ]
        """
        raise NotImplementedError
    
    @abstractmethod
    def get_metrics_by_pid(self, n: int):
        """
        Returns the last `n` metrics for all applications as list of dict,
        where the **first** element in the list is the **oldest**.

        Example:
        >>> get_metrics_by_pid(n=2)
        [
          {
            10042: {"instructions": 100, "cycles": 20, ... },
            424242: { "instructions": 200, "cycles": 40, ...  }
          },
          {
            10042: { ... },
            424242: { ... }
          }
        ]
        """
        raise NotImplementedError
    
    def get_core_frequencies(self, n: int) -> list[dict[int, float]]:
        """
        Returns the last `n` frequency measurements as a list of dict, 
        where the **first** element in the list is the **oldest** measurement.
        Each dict only contains the frequencies of those cores that were used by the monitored applications.

        Example:
        >>> get_core_frequencies(n=3)
        [
          { 2 : 3500, 16: 1500 },
          { 2 : 3300, 16: 1600 },
          { 2 : 3300           }, # Application on core 16 finished
        ]
        """
        raise NotImplementedError
    
    def get_total_events(self, application: Application) -> dict[str, int] | None:
        """
        Returns the total event counts for a given application.
        Note: The total counts are based on extrapolatd samples. This is done to counteract sampling induced blind spots

        Example:
        >>> get_total_events(application = app)
        {
          "instructions" : 20_000_000_000
          "cycles" : 8_000_000_000
          ...
        }
        """
        raise NotImplementedError

    @abstractmethod
    def get_lock(self) -> Lock:
        """
        Returns the lock of this buffer. This should primarly be used when multiple reads are performed.
        E.g. `get_metircs_by_pid(); get_system_metrics()`
        """
        raise NotImplementedError