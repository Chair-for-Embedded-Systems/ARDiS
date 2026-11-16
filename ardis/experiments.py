from pathlib import Path
import random
import sys

from ardis.benchmarks import Application, ParsecApplication
from ardis.core import Engine, EngineConfig, MappingPolicy, Scheduler, DVFSPolicy, MigrationPolicy, MonitoringMode, PostProcessor
from ardis.core.policies import StaticGovernorDVFS, GreedyScheduler, NextAvailableCoreMapping
import ardis.config as config

class CustomExperiment:
    """
    Fully customizable experiment class which allows the specification of all aspects of the experiment.
    """
    def __init__(
        self,
        engine_config: EngineConfig,
        applications: list[Application],
        postprocessor: PostProcessor | None = None
    ) -> None:
        self.__engine_config = engine_config
        self.__engine = Engine(engine_config=self.__engine_config)
        self.__applications = applications.copy()
        self.__postprocessor = postprocessor
    
    def executeExperiment(self) -> Path:
        """Execute the experiment and wait for it to finish. Returns the path to the results folder."""

        if len(self.__applications) == 0:
            raise ValueError("No applications set for the experiment. Please set applications before executing the experiment.")
        
        try:
            self.__engine.executeWorkload(self.__applications)
            results_path = Path(self.getWorkingDirectory())
            # Exeute postprocessing if a postprocessor is set
            if self.__postprocessor:
                self.__postprocessor.process(str(results_path))
            
            return results_path

        except KeyboardInterrupt:
            print("[Experiment] Interrupted by user")
            self.__engine.interrupt()
            sys.exit()


    def setApplications(self, applications: list[Application]) -> None:
        """
        Sets the applications to be executed in the experiment. If applications were already set, they will be replaced.
        """
        self.__applications = applications

    def setPostProcessor(self, postprocessor: PostProcessor) -> None:
        """
        Set a postprocessor to be used after the experiment is finished. 
        If a postprocessor was already set, it will be replaced.
        """
        self.__postprocessor = postprocessor

    def generateRandomApps(
        self,
        N_apps: int,
        unique: bool = True,
        application_pool: list[str] = config.parsec_apps,
        seed: int = 42
    ) -> None:
        """
        Generates a random worlkload of N_apps applications from the available parsec applications.
        """

        if N_apps < 1:
            raise ValueError("Number of applications must be at least 1")
        if len(application_pool) == 0:
            raise ValueError("Pool of available applications is empty")
        if unique and N_apps > len(application_pool):
            raise ValueError(f"Cannot generate {N_apps} unique applications from a pool of {len(application_pool)} applications.")
        
        rng = random.Random(seed)
        
        if unique:
            selected_apps = rng.sample(application_pool, N_apps)
        else:
            selected_apps = rng.choices(application_pool, k=N_apps)

        self.__applications : list[Application] = [ParsecApplication(app) for app in selected_apps]

    def getWorkingDirectory(self) -> str:
        return self.__engine.reporter.workdir

    def __str__(self):
        return f"Experiment {self.__engine_config.experiment_name} with applications {self.__applications} and engine {self.__engine}"
        
    def __repr__(self):
        return self.__str__()


class Experiment(CustomExperiment):

    """
    Simplified wrapper around the CustomExperiment that uses many default values for the engine configuration,
    to provide a more user-friendly interface for creating experiments.
    """

    def __init__(
        self, 
        name: str = "", 
        applications: list[Application] | None = None,
        scheduler: Scheduler | None = None,
        mapping_policy: MappingPolicy | None = None,
        dvfs_policy: DVFSPolicy | None = None,
        migration_policy: MigrationPolicy | None = None, 
        monitoring_mode: MonitoringMode = MonitoringMode.PERIODIC_ON_CORE,
        results_folder: str = config.RESULTS_FOLDER,
        postprocessor: PostProcessor | None = None,
    ):   

        # Sane defaults for the engine configuration, initialized here to avoid unintened sharing
        if scheduler is None:
            scheduler = GreedyScheduler()
        if mapping_policy is None:
            mapping_policy = NextAvailableCoreMapping(prefered_cores=list(range(config.system_cores)))
        if applications is None:
            applications = []

        cfg = EngineConfig(
            experiment_name=name,
            results_folder=results_folder,
            scheduler=scheduler,
            mapping_policy=mapping_policy,
            dvfs_policy=dvfs_policy,
            migration_policy=migration_policy,
            action_interval_ms=config.action_interval_sec * 1000,
            monitoring_interval_ms=config.sampling_rate_ms,
            monitoring_mode=monitoring_mode,
            monitoring_backend=config.monitoring_backend,
            periodic_app_level_events=tuple(config.periodic_app_level_events),
            periodic_system_wide_events=tuple(config.periodic_system_wide_events),
            periodic_system_wide_events_one_shot=tuple(config.one_shot_system_wide_events),
            monitor_core_temperatures=config.monitor_core_temperatures,
            runtime_temp_dir=config.RUNTIME_TEMP_DIR,
            debug=False
        )
        super().__init__(engine_config=cfg, applications=applications, postprocessor=postprocessor)


class DefaultLinuxExperiment(Experiment):
    """
    Wrapper around the Experiment class, 
    which provides a simplified interface to create experiments with different Linux DVFS governors.
    """    
    def __init__(
        self,
        name: str = "",
        applications: list[Application] | None = None,
        scheduler: Scheduler | None = None,
        governor: str = "performance",
        min_frequency_mhz: int = 1500,
        max_frequency_mhz: int = 3500,
        monitoring_mode: MonitoringMode = MonitoringMode.PERIODIC_ON_PID,
        mapping_policy: MappingPolicy | None = None,
        results_folder: str = config.RESULTS_FOLDER,
        postprocessor: PostProcessor | None = None,
    ):    
        super().__init__(
            name=name,
            applications=applications,
            scheduler=scheduler,
            mapping_policy=mapping_policy,
            dvfs_policy=StaticGovernorDVFS(
                governor=governor,
                min_frequency=min_frequency_mhz,
                max_frequency=max_frequency_mhz,
            ),
            migration_policy=None,
            monitoring_mode=monitoring_mode,
            results_folder=results_folder,
            postprocessor=postprocessor,
        )