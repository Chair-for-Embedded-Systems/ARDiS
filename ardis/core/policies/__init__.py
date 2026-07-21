# This file serves as a central hub for all policy-related imports.
# It consolidates the various policy classes from different submodules,
# making them easily accessible from a single location.

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    # Scheduling policies
    from .schedueling.consecutive_schedule import ConsecutiveScheduler
    from .schedueling.fixed_time_schedule import FixedTimeScheduler
    from .schedueling.greedy_schedule import GreedyScheduler

    # Mapping policies
    from .mapping.explicit_mapping import ExplicitMapping
    from .mapping.next_available_core import NextAvailableCoreMapping
    # from .mapping.intel_motivational_mapping import IntelMotivationalExample # (Leftover)
    
    # Migration policies
    from .migration.migrate_for_training import MigrationForTraining
    # from .migration.migrate_following_schedule import StaticScheduleMigration # (Leftover)
    
    # DVFS policies
    from .dvfs.static_dvfs import StaticDVFS, StaticGovernorDVFS
    # from .dvfs.intel_static_dvfs import IntelStaticDVFSPolicy # (Leftover)
    from .dvfs.dvfs_for_training import DVFSForTraining # (Leftover, still used in examples/policies.py)

__all__ = [
    # Scheduling policies
    'ConsecutiveScheduler',
    'FixedTimeScheduler',
    'GreedyScheduler',
    # Mapping policies
    'ExplicitMapping',
    'NextAvailableCoreMapping',
    #'IntelMotivationalExample', # (Leftover)
    
    # Migration policies
    'MigrationForTraining',
    #'StaticScheduleMigration', # (Leftover)
    
    # DVFS policies
    'StaticDVFS',
    'StaticGovernorDVFS',
    #'IntelStaticDVFSPolicy', # (Leftover)
    'DVFSForTraining' # (Leftover, still used in examples/policies.py)
]

_LAZY_IMPORTS = {
    # Scheduling policies
    'ConsecutiveScheduler': '.schedueling.consecutive_schedule',
    'FixedTimeScheduler': '.schedueling.fixed_time_schedule',
    'GreedyScheduler': '.schedueling.greedy_schedule',
    
    # Mapping policies
    'ExplicitMapping': '.mapping.explicit_mapping',
    'NextAvailableCoreMapping': '.mapping.next_available_core',
    #'IntelMotivationalExample': '.mapping.intel_motivational_mapping', # (Leftover)
    
    # Migration policies
    'MigrationForTraining': '.migration.migrate_for_training',
    #'StaticScheduleMigration': '.migration.migrate_following_schedule', # (Leftover)
    
    # DVFS policies
    'StaticDVFS': '.dvfs.static_dvfs',
    'StaticGovernorDVFS': '.dvfs.static_dvfs',
    #'IntelStaticDVFSPolicy': '.dvfs.intel_static_dvfs', # (Leftover)
    'DVFSForTraining': '.dvfs.dvfs_for_training', # (Leftover, still used in examples/policies.py)
}

def __getattr__(name: str):
    """Dynamically import and return the requested attribute."""
    if name in _LAZY_IMPORTS:
        # Perform the import only when the name is accessed
        import importlib
        module_path = _LAZY_IMPORTS[name]
        
        # importlib.import_module handles relative imports if we pass __package__
        module = importlib.import_module(module_path, __package__)
        obj = getattr(module, name)
        
        # Cache it in the module's globals so subsequent lookups are instant
        globals()[name] = obj
        return obj
        
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")

def __dir__():
    """Ensure tab-completion in interactive shells still works perfectly."""
    return sorted(list(globals().keys()) + __all__)