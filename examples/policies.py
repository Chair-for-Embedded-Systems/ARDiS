from ardis.benchmarks import ParsecApplication
from ardis.core import MonitoringMode
from ardis.core.policies import MigrationForTraining, DVFSForTraining, ExplicitMapping, ConsecutiveScheduler
from ardis.core.postprocessing import ClipPostProcessor
from ardis.core.postprocessing.clips import AppMappingClip, SystemFrequencyClip
from ardis.experiments import Experiment


def run_example_with_random_migration_and_random_dvfs():
    # Create an experiment object
    exp = Experiment(
        name="Simple Experiment with random dvfs and app migration", 
        mapping_policy=ExplicitMapping.from_list([2, 16]),
        scheduler=ConsecutiveScheduler(delay_sec=0),
        migration_policy=MigrationForTraining(
            migrate_within_cluster=True,
            epoch_trigger_intervall=5,
        ),
        dvfs_policy=DVFSForTraining(
            p_core_range=list(range(3500, 4501, 100)),
            e_core_range=list(range(2000, 3001, 100))
        ),
        applications=[
            ParsecApplication('parsec.blackscholes'),
            ParsecApplication('parsec.dedup')
        ],
        monitoring_mode=MonitoringMode.PERIODIC_ON_PID,
    )
    # The default FrequencyClip uses line plots to visualize frequencies, which can be misleading if the data is sparse
    # (e.g due to frequent migrations). Here we want to use a scatter plot instead.
    # Therefore we use ClipPostProcessor instead of SimpleClipPostProcessor to customize the clip.
    exp.setPostProcessor(ClipPostProcessor(
        clips=[
            AppMappingClip(),
            SystemFrequencyClip(
                use_scatter=True,  # Use scatter plot instead of line plot
                cores={2, 4, 16, 18}, # Only show frequencies for these cores
                skip_unavailable_cores=True # Disable check, since a bit of randomness is involved
                )
            ],
        verbose=True
    ))

    exp.executeExperiment()

if __name__ == "__main__":
    run_example_with_random_migration_and_random_dvfs()