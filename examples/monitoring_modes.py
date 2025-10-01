from ardis.benchmarks import ParsecApplication
import ardis.config as config

from ardis.core import *
from ardis.core.policies import ExplicitMapping, ConsecutiveScheduler, StaticDVFS
from ardis.core.postprocessing import SimpleClipPostProcessor
from ardis.core.postprocessing.simple_clip_postprocessor import Clips
from ardis.experiments import Experiment

def run_example_with_core_monitoring():
   # Create an experiment object
    exp = Experiment(name="Simple Experiment with Specific Applications", 
                     mapping_policy=ExplicitMapping([{3}, {6}, {19}]),
                     scheduler=ConsecutiveScheduler(0),
                     dvfs_policy=StaticDVFS({core: 3000 for core in range(config.system_cores)}),
                     monitoring_mode=MonitoringMode.PERIODIC_ON_CORE)
    
    # Manually set the applications to execute
    exp.setApplications([
        ParsecApplication("parsec.blackscholes"),
        ParsecApplication("parsec.bodytrack"),
        ParsecApplication("splash2x.radix")
    ])
    # Run the experiment
    exp.executeExperiment()

def run_example_with_pid_monitoring():
   # Create an experiment object
    exp = Experiment(
        name="Simple Experiment with Specific Applications", 
        applications=[
            ParsecApplication("parsec.blackscholes"),
            ParsecApplication("parsec.dedup"),
        ],
        mapping_policy=ExplicitMapping.from_list([6, 19]),
        scheduler=ConsecutiveScheduler(0),
        dvfs_policy=StaticDVFS({core: 3000 for core in range(config.system_cores)}),
        monitoring_mode=MonitoringMode.PERIODIC_ON_PID
    )

    # Run the experiment
    exp.executeExperiment()

def run_example_with_tid_monitoring():
    exp = Experiment(
        name="Experiment_with_tid_monitoring",
        applications=[
            ParsecApplication("parsec.dedup", 4),
        ],
        mapping_policy=ExplicitMapping([{2, 4, 6, 8}]),
        scheduler=ConsecutiveScheduler(0),
        dvfs_policy=StaticDVFS({core: 3500 for core in range(config.system_cores)}),
        monitoring_mode=MonitoringMode.PERIODIC_ON_TID,
        postprocessor=SimpleClipPostProcessor(
            clips=[
                Clips.APP_METRICS_ALL,
                Clips.THREAD_EXECUTION_OVERVIEW, Clips.THREAD_MAPPING,
                Clips.SYSTEM_METRICS_ALL
            ],
            verbose=True,
        )
    )
    exp.executeExperiment()

if __name__ == "__main__":
    run_example_with_core_monitoring()
    run_example_with_pid_monitoring()
    run_example_with_tid_monitoring()