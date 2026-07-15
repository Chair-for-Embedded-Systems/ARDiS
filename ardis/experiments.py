import sys
from random import randrange

from ardis.benchmarks import Application, ParsecApplication
from ardis.core import Engine, MappingPolicy, Scheduler, DVFSPolicy, MigrationPolicy, MonitoringMode, PostProcessor
from ardis.core.policies import StaticGovernorDVFS, ConsecutiveScheduler
from ardis.core.mapping import NextAvailableCoreMapping

import ardis.config as config


class Experiment:
    def __init__(
        self, 
        name: str="", 
        applications: list[Application] = [],
        mapping_policy: MappingPolicy = NextAvailableCoreMapping(prefered_cores=list(range(config.system_cores))), # Default mapping policy
        scheduler: Scheduler = ConsecutiveScheduler(delay_sec=0), # Default scheduler
        dvfs_policy: DVFSPolicy | None = None, # No default to avoid multiple instances of a frequency manager
        migration_policy: MigrationPolicy | None = None, 
        monitoring_mode: MonitoringMode = MonitoringMode.PERIODIC_ON_CORE,
        results_folder: str = config.RESULTS_FOLDER,
        postprocessor: PostProcessor | None = None,
    ):   
        self.__name = name
        self.__applications = applications
        self.__postprocessor = postprocessor

        self.__engine = Engine(
            experiment_name=self.__name, 
            mapping_policy=mapping_policy, 
            scheduler=scheduler, 
            dvfs_policy=dvfs_policy, 
            migration_policy=migration_policy, 
            monitoring_mode=monitoring_mode,
            results_folder=results_folder
        )
        
    # Generate a random list of N unique applications to execute
    def generateRandomApps(self,  N_apps: int, unique: bool = True):
        selected_apps: list[str] = []
        application_pool = config.parsec_apps 

        while len(selected_apps) < N_apps:
            candidate = application_pool[randrange(len(application_pool))]
            if unique and candidate in selected_apps:
                continue
            self.__applications.append(ParsecApplication(candidate))
    
    def setApplications(self, applications: list[Application]):
        self.__applications = applications
   
    # Execute the experiment and wait for it to finish
    def executeExperiment(self):
        try:
            self.__engine.executeWorkload(self.__applications)
            if self.__postprocessor:
                self.__postprocessor.process(self.getWorkingDirectory())
        except KeyboardInterrupt:
            print("Experiment interrupted by user")
            self.__engine.interrupt()
            sys.exit()
            return
    
    def setPostProcessor(self, postprocessor: PostProcessor):
        """
        Set a postprocessor to be used after the experiment is finished. 
        If a postprocessor was already set, it will be replaced.
        """
        self.__postprocessor = postprocessor

    def getWorkingDirectory(self):
        return self.__engine.reporter.workdir

    def __str__(self):
        return f"Experiment {self.__name} with applications {self.__applications} and engine {self.__engine}"
    
    def __repr__(self):
        return self.__str__()
    
    

class DefaultLinuxExperiment:
    def __init__(
        self,
        name: str = "",
        applications: list[Application] = [],
        scheduler: Scheduler = ConsecutiveScheduler(delay_sec=0),
        governor: str = "performance",
        min_frequency_mhz: int = 1500,
        max_frequency_mhz: int = 3500,
        monitoring_mode: MonitoringMode = MonitoringMode.PERIODIC_ON_PID,
        mapping_policy: MappingPolicy = NextAvailableCoreMapping(prefered_cores=list(range(config.system_cores))),
    ):
        self.__name = name
        self.__applications = applications
        
        self.__engine = Engine(
            experiment_name=self.__name, 
            mapping_policy=mapping_policy, 
            scheduler=scheduler, 
            dvfs_policy=StaticGovernorDVFS(governor=governor, min_frequency=min_frequency_mhz, max_frequency=max_frequency_mhz), 
            migration_policy=None, 
            monitoring_mode=monitoring_mode
        )
        
    
    def setApplications(self, applications: list[Application]):
        self.__applications = applications
   
    # Execute the experiment and wait for it to finish
    def executeExperiment(self):
        self.__engine.executeWorkload(self.__applications)
    
    def __str__(self):
        return f"Experiment {self.__name} with applications {self.__applications} and engine {self.__engine}"
    
    def __repr__(self):
        return self.__str__()