import random

import ardis.config as config
from ardis.core.migration import MigrationPolicy, MigrationAction, SystemState

class MigrationForTraining(MigrationPolicy):
    def __init__(self, migrate_within_cluster=True, epoch_trigger_intervall: int = 10):
        super().__init__()
        self._migrate_within_cluster = migrate_within_cluster
        self._epoch_trigger_intervall = epoch_trigger_intervall
    
    def get_migration_actions(self, system_state: SystemState) -> list[MigrationAction]:
        
        if system_state.epoch % self._epoch_trigger_intervall != 0:
            return []

        # List of P-core and E-core IDs from the config
        intel_p_core_ids = config.intel_p_core_ids
        intel_e_core_ids_cluster_1 = config.intel_e_core_ids_cluster_1
        intel_e_core_ids_cluster_2 = config.intel_e_core_ids_cluster_2

        # Combine E-core clusters
        all_e_core_ids = intel_e_core_ids_cluster_1 + intel_e_core_ids_cluster_2

        # Randomly choose one application to migrate
        active_apps = [app for app, pid in system_state.app_to_pid.items() if pid != -1]
        if not active_apps:
            return []
        
        app_to_migrate = random.choice(active_apps)

        # Get the current core where the app is mapped
        current_cores = system_state.app_to_cores[app_to_migrate].copy()
        if len(current_cores) != 1:
            raise ValueError("Policy does not support multi-core mappings")
        
        current_core = current_cores.pop()

        # Determine if the current core is a P-core or E-core
        is_p_core = current_core in intel_p_core_ids
        is_e_core_cluster_1 = current_core in intel_e_core_ids_cluster_1
        is_e_core_cluster_2 = current_core in intel_e_core_ids_cluster_2

        new_core = None

        # Collect all currently occupied cores
        occupied_cores: set[int] = system_state.occupied_cores

        # If migrate_within_cluster is True, we migrate within the same core type or cluster
        if self._migrate_within_cluster:
            if is_p_core:
                # Migrate to another P-core
                available_cores = [core for core in intel_p_core_ids if core not in occupied_cores]
            elif is_e_core_cluster_1:
                # Migrate to another core within E-core cluster 1
                available_cores = [core for core in intel_e_core_ids_cluster_1 if core not in occupied_cores]
            else:
                # Migrate to another core within E-core cluster 2
                available_cores = [core for core in intel_e_core_ids_cluster_2 if core not in occupied_cores]
        else:
            # If migrate_within_cluster is False, migrate between core types or between clusters
            if is_p_core:
                # Migrate from P-core to an E-core (either cluster)
                available_cores = [core for core in all_e_core_ids if core not in occupied_cores]
            elif is_e_core_cluster_1 or is_e_core_cluster_2:
                # Migrate from E-core (either cluster) to a P-core
                available_cores = [core for core in intel_p_core_ids if core not in occupied_cores]
            else:
                available_cores = []  # Safety check, should not occur

        # Randomly select a new core from the available options
        if available_cores:
            new_core = random.choice(available_cores)
        else:
            return []

        action = MigrationAction(
            app=app_to_migrate,
            source=system_state.app_to_cores[app_to_migrate],
            destination={new_core}
        )

        return [action]