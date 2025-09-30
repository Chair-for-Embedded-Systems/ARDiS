from ardis.benchmarks import ParsecApplication
from ardis.core import MonitoringMode
from ardis.core.policies import ExplicitMapping, ConsecutiveScheduler, StaticDVFS
from ardis import config
from ardis.experiments import Experiment


def run_example_with_core_monitoring():
   # Create an experiment object
    exp = Experiment(
        name="Simple Experiment with Specific Applications", 
        mapping_policy=ExplicitMapping([{3}, {6}, {19}]),
        scheduler=ConsecutiveScheduler(0),
        dvfs_policy=StaticDVFS({core: 3000 for core in range(config.system_cores)}),
        monitoring_mode=MonitoringMode.PERIODIC_ON_CORE
    )
    
    # Manually set the applications to execute
    exp.setApplications([
        ParsecApplication("parsec.blackscholes"),
        ParsecApplication("parsec.bodytrack"),
        ParsecApplication("splash2x.radix")
    ])
    # Run the experiment
    exp.executeExperiment()

if __name__ == "__main__":
    run_example_with_core_monitoring()
    
