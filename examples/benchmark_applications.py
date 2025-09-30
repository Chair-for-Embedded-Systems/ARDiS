from ardis.benchmarks import ParsecApplication, BinaryApplication, SpecApplication
from ardis.benchmarks.application import Application
import ardis.config as config

from ardis.core import MonitoringMode
from ardis.core.policies import ExplicitMapping, ConsecutiveScheduler, StaticDVFS
from ardis.core.postprocessing.clip_postprocessor import ClipPostProcessor
from ardis.core.postprocessing.clips.app_multi_metric_clip import AppMultiMetricClip
from ardis.core.postprocessing.simple_clip_postprocessor import Clips, SimpleClipPostProcessor
from ardis.experiments import Experiment

def run_example_with_custom_binary():
    exp = Experiment(
        name="Experiment with custom binary",
        scheduler=ConsecutiveScheduler(0),
        applications=[
            BinaryApplication(start_command="/bin/sleep 10"),
            BinaryApplication(start_command="/bin/openssl speed sha256")
        ],
        mapping_policy=ExplicitMapping.from_list([2, 4]),
        dvfs_policy=StaticDVFS(),
        monitoring_mode=MonitoringMode.PERIODIC_ON_PID
    )
    exp.executeExperiment()

def run_all_spec2006_benchmarks():
    for package_name in config.spec_apps:
        exp = Experiment(
            name=f"Spec_experiment_{package_name}",
            scheduler=ConsecutiveScheduler(0),
            applications=[
                SpecApplication(package_name, SpecApplication.InputSize.TRAIN)
            ],
            mapping_policy=ExplicitMapping.from_list([8]),
            dvfs_policy=StaticDVFS({8: 4500}, base_frequency_mhz=3800),
            monitoring_mode=MonitoringMode.PERIODIC_ON_PID
        )
        exp.setPostProcessor(ClipPostProcessor(clips=[AppMultiMetricClip(["instructions"])]))
        exp.executeExperiment()


def run_example_with_multiple_instances():
    
    configs: list[tuple[int, Application, int]] = [
        (2, ParsecApplication('parsec.blackscholes'), 4800),
        (4, ParsecApplication('parsec.blackscholes'), 3500),
        (6, ParsecApplication('parsec.blackscholes'), 1500),
        (8, ParsecApplication('parsec.blackscholes'), 800),
    ]
    cores, apps, freq = zip(*configs)
    core_to_freq= dict(zip(cores, freq))
    
    exp = Experiment(
        name="Experiment with multiple instances",
        scheduler=ConsecutiveScheduler(0),
        applications=list(apps),
        mapping_policy=ExplicitMapping.from_list(list(cores)),
        dvfs_policy=StaticDVFS(core_to_freq, base_frequency_mhz=2200),
        monitoring_mode=MonitoringMode.PERIODIC_ON_PID,
        postprocessor=SimpleClipPostProcessor(
            clips=[Clips.APP_MAPPING, Clips.SYSTEM_CORE_FREQUENCY],
            verbose=True
        )
    )
    exp.executeExperiment()


if __name__ == "__main__":
    run_all_spec2006_benchmarks()
    run_example_with_custom_binary()
    run_example_with_multiple_instances()