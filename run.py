from ardis.benchmarks import ParsecApplication
from ardis.core import MonitoringMode
from ardis.core.policies import ExplicitMapping, ConsecutiveScheduler, StaticDVFS
from ardis.core.postprocessing.simple_clip_postprocessor import SimpleClipPostProcessor, Clips
from ardis.experiments import Experiment

# For additional examples, see the experiments directory in the repository root.
def run_example():
   # Create an experiment object
    exp = Experiment(
        name="Simple Experiment with Specific Applications", 
        mapping_policy=ExplicitMapping([{2}, {4}, {16}, {20}]),
        scheduler=ConsecutiveScheduler(0),
        dvfs_policy=StaticDVFS(
            core_to_frequency_mhz={ 2: 4300, 4: 4000, 16: 3800, 20: 2800 },
            base_frequency_mhz=3000
        ),
        monitoring_mode=MonitoringMode.PERIODIC_ON_PID
    )
    # Manually set the applications to execute
    exp.setApplications([
        ParsecApplication("parsec.blackscholes"),
        ParsecApplication("splash2x.fft"),
        ParsecApplication("parsec.dedup"),
        ParsecApplication("splash2x.radix")
    ])
    # Set the postprocessor to create specific clips
    exp.setPostProcessor(SimpleClipPostProcessor(
        clips=[
            Clips.APP_EXECUTION_OVERVIEW, 
            Clips.APP_METRICS_ALL,
            Clips.SYSTEM_CORE_FREQUENCY,
            Clips.SYSTEM_METRICS_ALL
        ],
        formats={"png"},
        verbose=True
    ))
    # Run the experiment
    exp.executeExperiment()

if __name__ == "__main__":
    run_example()
    