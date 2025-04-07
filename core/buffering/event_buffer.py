from abc import abstractmethod
class EventBuffer:

    @abstractmethod
    def push_core_events(self,
                        app_events: dict[int, dict[str, int|float]],
                        system_events: dict[str, int|float]
                        ) -> None:
        """Adds the given core events to the buffer."""
        raise NotImplementedError

    @abstractmethod
    def push_pid_events(self,
                       app_events: dict[int, dict[str, int|float]],
                       system_events: dict[str, int|float]
                       ) -> None:
        """Adds the given pid events to the buffer."""
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