from pathlib import Path
from ardis.benchmarks import ParsecApplication
import ardis.config as config
from ardis.core import MonitoringMode
from ardis.core.policies import ExplicitMapping, ConsecutiveScheduler, StaticDVFS
from ardis.core.postprocessing import SimpleClipPostProcessor
from ardis.core.postprocessing.simple_clip_postprocessor import Clips
from ardis.experiments import Experiment

def run_example_with_result_plotting() -> Path:
    
    exp = Experiment("Experiment with result plotting", 
                     mapping_policy=ExplicitMapping.from_list([3, 6, 17, 21]),
                     scheduler=ConsecutiveScheduler(0),
                     dvfs_policy=StaticDVFS({core: 3000 for core in range(config.system_cores)}),
                     monitoring_mode=MonitoringMode.PERIODIC_ON_PID)
    
    exp.setApplications([
        ParsecApplication('parsec.blackscholes'),
        ParsecApplication('parsec.bodytrack'),
        ParsecApplication('splash2x.radix'),
        ParsecApplication('splash2x.radiosity'),
        
    ])
    exp.setPostProcessor(
        SimpleClipPostProcessor(
            clips=[Clips.APP_METRICS_ALL, Clips.APP_EXECUTION_OVERVIEW, Clips.SYSTEM_CORE_FREQUENCY],
            verbose=True,
        )
    )
    exp.executeExperiment()

    return Path(exp.getWorkingDirectory())  

def run_example_with_df_provider(experiment_folder: Path) -> None:
    from ardis.core.postprocessing import ExperimentResultWrapper
    
    result_wrapper = ExperimentResultWrapper(experiment_folder)

    # Access the dataframe provider to get experiment data as pandas DataFrames
    df_provider = result_wrapper.get_df_provider()

    app_level_df = df_provider.get_app_level_dataframe()
    system_metrics_df = df_provider.get_system_metrics_dataframe()
    # temperature_df = df_provider.get_temperature_dataframe() # If available

    print("Application-level DataFrame:")
    print(app_level_df.head())

    print("System metrics DataFrame:")
    print(system_metrics_df.head())

if __name__ == "__main__":
    exp = run_example_with_result_plotting()
    run_example_with_df_provider(exp)