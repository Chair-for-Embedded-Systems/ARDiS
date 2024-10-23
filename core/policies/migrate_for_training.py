from core.migration import *
import sys, os

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

class MigrationForTraining(MigrationPolicy):
    def __init__(self, migrate_within_cluster=True):
        super().__init__()
        self._migrate_within_cluster = migrate_within_cluster
    
    def getNewMapping(self, instructions, mapping):
        # List of P-core and E-core IDs from the config
        intel_p_core_ids = config.intel_p_core_ids
        intel_e_core_ids_cluster_1 = config.intel_e_core_ids_cluster_1
        intel_e_core_ids_cluster_2 = config.intel_e_core_ids_cluster_2

        # Combine E-core clusters
        all_e_core_ids = intel_e_core_ids_cluster_1 + intel_e_core_ids_cluster_2

        # Randomly choose one application to migrate
        app_to_migrate = random.choice(list(mapping.keys()))

        # Get the current core where the app is mapped
        current_core = mapping[app_to_migrate]

        # Determine if the current core is a P-core or E-core
        is_p_core = current_core in intel_p_core_ids
        is_e_core_cluster_1 = current_core in intel_e_core_ids_cluster_1
        is_e_core_cluster_2 = current_core in intel_e_core_ids_cluster_2

        new_core = None

        # Collect all currently occupied cores
        occupied_cores = set(mapping.values())

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

        # Create the new mapping with the selected application migrated to the new core
        new_mapping = mapping.copy()
        if new_core is not None:
            new_mapping[app_to_migrate] = new_core

        #print(f"Migrating {app_to_migrate} from core {current_core} to core {new_core}")
        return new_mapping