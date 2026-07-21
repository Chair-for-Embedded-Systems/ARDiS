import ardis.config as config

from ardis.core.mapping import MappingPolicy, Application, SystemState, MappingException

class NextAvailableCoreMapping(MappingPolicy):
    """
    This mapping policy assigns applications to the next available cores.
    It prioritizes cores based on the order specified in `prefered_cores`.
    """
    def __init__(
        self,
        prefered_cores: list[int] = list(range(config.system_cores))
    ) -> None:
        """
        Parameters:
            - prefered_cores: List of cores to prioritize for mapping applications (descending order of preference).
        """
        super().__init__(set(prefered_cores))
        self._prefered_order = list(prefered_cores)

    def register_workload(self, workload: list[Application]) -> None:
        # No precomputation needed for this simple mapping policy
        return

    def get_mapping(self, application: Application, system_state: SystemState) -> set[int]:
        
        required_core = application.get_preffered_core_count()

        mapping : set[int] = set()
        occupied_cores = system_state.occupied_cores

        for core in self._prefered_order:
            if core in occupied_cores:
                continue
            mapping.add(core)
            if len(mapping) == required_core:
                break

        if len(mapping) < required_core:
            raise MappingException(
                f"Not enough available cores to map application {application}."
                f"Required: {required_core}, Available: {len(self._prefered_order) - len(occupied_cores)}"
            )

        return mapping