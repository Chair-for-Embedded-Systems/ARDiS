from ardis.core.mapping import MappingPolicy, Application, SystemState

class NextAvailableCoreMapping(MappingPolicy):
    
    def __init__(self, prefered_cores: list[int]):
        super().__init__(set(prefered_cores))
        self._prefered_order = list(prefered_cores)

    def register_workload(self, workload: list[Application]) -> None:
        # No precomputation needed for this simple mapping policy
        return

    def get_mapping(self, application: Application, system_state: SystemState) -> set[int]:
        
        required_core = 1 # Currently, we assume that each application requires only one core. This can be extended in the future.

        mapping : set[int] = set()
        occupied_cores = system_state.occupied_cores

        for core in self._prefered_order:
            if core in occupied_cores:
                continue
            mapping.add(core)
            if len(mapping) == required_core:
                break

        return self._mapping[application]