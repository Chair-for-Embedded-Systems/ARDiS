from ardis.core.mapping import MappingPolicy, Application, SystemState, MappingException

class NextAvailableCoreMapping(MappingPolicy):
    
    def __init__(self, prefered_cores: list[int]):
        """
        Parameters:
            - prefered_cores: List of cores to prioritize for mapping applications, in descending order of preference.
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
            raise MappingException(f"Not enough available cores to map application {application}. Required: {required_core}, Available: {len(self._prefered_order) - len(occupied_cores)}")

        return self._mapping[application]