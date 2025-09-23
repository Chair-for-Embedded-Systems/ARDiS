from config import *
from core.engine import *
from core.policies.explicit_mapping import *
from core.policies.migrate_following_schedule import *
from core.policies.dvfs_for_training import *
from core.policies.migrate_for_training import *
from core.policies.consecutive_schedule import *
from core.policies.intel_static_dvfs import *
from core.policies.static_dvfs import StaticDVFS, StaticGovernorDVFS
from core.dvfs import *
from core.monitoringmode import *
from core.migration import *
from core.policies.intel_motivational_mapping import *
from core.postprocessing.result_plotter import BasicResultPlotter, Diagrams
from benchmarks import Application, ParsecApplication, BinaryApplication, SpecApplication
from random import randrange
import os




class Experiment:
    def __init__(
        self, 
        name: str="", 
        applications: list[Application] = [],
        mapping_policy: MappingPolicy = MappingPolicy(),
        scheduler: Scheduler = Scheduler(), 
        dvfs_policy: DVFSPolicy | None = None, # No default to avoid multiple instances of a frequency manager
        migration_policy: MigrationPolicy | None = None, 
        monitoring_mode: MonitoringMode = MonitoringMode.PERIODIC_ON_CORE,
        results_folder: str = RESULTS_FOLDER
    ):   
        self.__name = name
        self.__applications = applications
        self.__engine = Engine(self.__name, 
                       mapping_policy=mapping_policy, 
                       scheduler=scheduler, 
                       dvfs_policy=dvfs_policy, 
                       migration_policy=migration_policy, 
                       monitoring_mode=monitoring_mode,
                       results_folder=results_folder)

    # Generate a random list of N unique applications to execute
    def generateRandomApps(self, N_apps):
        
        while len(self.__applications) < N_apps:
            candidate = parsec_apps[randrange(len(parsec_apps))]
            if candidate not in self.__applications:
                self.__applications.append(ParsecApplication(candidate))
    
    def setApplications(self, applications: list[Application]):
        self.__applications = applications
   
    # Execute the experiment and wait for it to finish
    def executeExperiment(self):
        try:
            self.__engine.executeWorkload(self.__applications)
        except KeyboardInterrupt:
            print("Experiment interrupted by user")
            self.__engine.stop_engine()
            return
    
    def getWorkingDirectory(self):
        return self.__engine.reporter.workdir

    def __str__(self):
        return f"Experiment {self.__name} with applications {self.__applications} and engine {self.__engine}"
    
    def __repr__(self):
        return self.__str__()
    
    

class DefaultLinuxExperiment:
    def __init__(self, name="", applications=[], scheduler=Scheduler(), governor="performance", min_frequency=1500, max_frequency=3500, monitoring_mode=MonitoringMode.PERIODIC_ON_PID, mapping_policy=MappingPolicy()):
        self.__name = name
        self.__applications = applications
        self.__engine = Engine(self.__name, 
                       mapping_policy=mapping_policy, 
                       scheduler=scheduler, 
                       dvfs_policy=StaticGovernorDVFS(governor=governor, min_frequency=min_frequency, max_frequency=max_frequency), 
                       migration_policy=None, 
                       monitoring_mode=monitoring_mode)
    
    def setApplications(self, applications: list[Application]):
        self.__applications = applications
   
    # Execute the experiment and wait for it to finish
    def executeExperiment(self):
        self.__engine.executeWorkload(self.__applications)
    
    def __str__(self):
        return f"Experiment {self.__name} with applications {self.__applications} and engine {self.__engine}"
    
    def __repr__(self):
        return self.__str__()


def run_example_with_core_monitoring():
   # Create an experiment object
    exp = Experiment("Simple Experiment with Specific Applications", 
                     mapping_policy=ExplicitMapping.from_list([3, 6, 19]),
                     scheduler=ConsecutiveScheduler(0),
                     dvfs_policy=StaticDVFS({core: 3000 for core in range(system_cores)}),
                     monitoring_mode=MonitoringMode.PERIODIC_ON_CORE)
    # Manually set the applications to execute
    exp.setApplications([
        ParsecApplication("parsec.blackscholes"),
        ParsecApplication("parsec.bodytrack"),
        ParsecApplication("splash2x.radix")
    ])
    # Run the experiment
    exp.executeExperiment()

def run_example_with_PID_monitoring():
   # Create an experiment object
    exp = Experiment("Simple Experiment with Specific Applications", 
                     applications=[
                         ParsecApplication("parsec.blackscholes"),
                         ParsecApplication("parsec.dedup"),
                     ],
                     mapping_policy=ExplicitMapping.from_list([6, 19]),
                     scheduler=ConsecutiveScheduler(0),
                     dvfs_policy=StaticDVFS({core: 3000 for core in range(system_cores)}),
                     monitoring_mode=MonitoringMode.PERIODIC_ON_PID)
    # Manually set the applications to execute
    #exp.setApplications(['parsec-blackscholes'])
    # Run the experiment
    exp.executeExperiment()


def run_parsec_default_linux_governor_simple():

    scheduler=ConsecutiveScheduler(0)      
    governor = "performance"
    app = ParsecApplication("splash2x.radix")
    exp_name = f"{app}_{governor}"
    exp = DefaultLinuxExperiment(exp_name, 
                    scheduler=scheduler,
                    mapping_policy=ExplicitMapping.from_list([6, 19]),
                    governor=governor,
                    min_frequency=1500,
                    max_frequency=3500,
                    monitoring_mode=MonitoringMode.PERIODIC_ON_PID)
                    
    exp.setApplications([app])
    exp.executeExperiment()


def run_parsec_default_linux_governor():

    scheduler=ConsecutiveScheduler(0)      

    for governor in ["performance", "powersave", "ondemand", "conservative", "schedutil"]:
        for app in parsec_apps:
            #governor = "performance"
            #app = "parsec-blackscholes"
            exp_name = f"{app}_{governor}"
            if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                exp = DefaultLinuxExperiment(exp_name, 
                                scheduler=scheduler, 
                                governor=governor,
                                min_frequency=1500,
                                max_frequency=3500,
                                monitoring_mode=MonitoringMode.PERIODIC_ON_CORE)
                                
                exp.setApplications([ParsecApplication(app)])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")

                
def run_parsec_characterization_experiments():

    scheduler=ConsecutiveScheduler(0)                   
    for frequency in [3500, 3400, 3300, 3200, 3100, 3000, 2900, 2800, 2700, 2600, 2500, 2400, 2300, 2200, 2100, 2000, 1900, 1800, 1700, 1600, 1500]:    
        #run on a P core
        for app in parsec_apps:
            exp_name = f"{app}_{frequency}MHz_Pcore"
            if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping.from_list([intel_p_core_ids[3]]), 
                                scheduler=scheduler, 
                                dvfs_policy=StaticDVFS({core: frequency for core in range(system_cores)}),
                                monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
                                results_folder=config.RESULTS_FOLDER)
                exp.setApplications([ParsecApplication(app)])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")
        #run on an E core
        for app in parsec_apps:
            exp_name = f"{app}_{frequency}MHz_Ecore"
            if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping.from_list([intel_e_core_ids[0]]), 
                                scheduler=scheduler, 
                                dvfs_policy=StaticDVFS({core: frequency for core in range(system_cores)}),
                                monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
                                results_folder=config.RESULTS_FOLDER)
                exp.setApplications([ParsecApplication(app)])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")


def run_example_with_result_plotting():
    
    exp = Experiment("Experiment with result plotting", 
                     mapping_policy=ExplicitMapping.from_list([3, 6, 19]),
                     scheduler=ConsecutiveScheduler(0),
                     dvfs_policy=StaticDVFS({core: 3000 for core in range(system_cores)}),
                     monitoring_mode=MonitoringMode.PERIODIC_ON_PID)
    
    exp.setApplications([
        ParsecApplication('parsec.blackscholes'),
        ParsecApplication('splash2x.radix'),
        ParsecApplication('parsec.bodytrack')
    ])
    exp.executeExperiment()
    
    # Plots the diagrams
    result_plt =  BasicResultPlotter(
        experiment_folder=exp.getWorkingDirectory(),
        diagrams=[Diagrams.FREQUENCY, Diagrams.INSTRUCTIONS, Diagrams.MAPPING], # Leave undefined for all diagrams
        #aoi="parsec-blackscholes" # Specify an application of interest, leave undefined for all apps
        ) 
    result_plt.plot_results(verbose=True)

def run_example_with_TID_monitoring():
    exp = Experiment(
        name="Experiment_with_tid_monitoring",
        applications=[
            ParsecApplication("parsec.dedup", 4),
            ParsecApplication("splash2x.radix", 1),
        ],
        mapping_policy=ExplicitMapping([{2, 4, 6, 8}, {16}]),
        scheduler=ConsecutiveScheduler(0),
        dvfs_policy=StaticDVFS({core: 3500 for core in range(system_cores)}),
        monitoring_mode=MonitoringMode.PERIODIC_ON_TID
    )
    exp.executeExperiment()
    rp = BasicResultPlotter(
        experiment_folder=exp.getWorkingDirectory(),
        diagrams=[Diagrams.EXECUTION_OVERVIEW, Diagrams.INSTRUCTIONS, Diagrams.MAPPING, Diagrams.FREQUENCY]
    )
    rp.plot_results(verbose=True)

def run_example_with_random_migration_and_random_dvfs():
    # Create an experiment object
    exp = Experiment(
        name="Simple Experiment with random dvfs and app migration", 
        mapping_policy=ExplicitMapping.from_list([6, 16]),
        scheduler=ConsecutiveScheduler(delay=0),
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
        monitoring_mode=MonitoringMode.PERIODIC_ON_PID
    )
    exp.executeExperiment()
    rp = BasicResultPlotter(experiment_folder=exp.getWorkingDirectory(), diagrams=[Diagrams.MAPPING, Diagrams.FREQUENCY])
    rp.plot_results(verbose=True)

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
        monitoring_mode=MonitoringMode.PERIODIC_ON_PID
    )
    exp.executeExperiment()

    rp = BasicResultPlotter(experiment_folder=exp.getWorkingDirectory(), diagrams=[Diagrams.MAPPING, Diagrams.FREQUENCY])
    rp.plot_results(verbose=True)

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
    for package_name in spec_apps:
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
        exp.executeExperiment()
        try:
            rp = BasicResultPlotter(experiment_folder=exp.getWorkingDirectory(), diagrams=[Diagrams.INSTRUCTIONS])
            rp.plot_results(verbose=True)
        except Exception as e:
            print(f"Could not plot results for SPEC benchmark {package_name}: {e}")

if __name__ == "__main__":
    #run_example_with_core_monitoring()
    #run_example_with_PID_monitoring()
    #run_parsec_default_linux_governor()
    #run_parsec_characterization_experiments()
    #run_example_with_result_plotting()
    #run_example_with_TID_monitoring()
    #run_example_with_random_migration_and_random_dvfs()
    run_example_with_multiple_instances()
    run_example_with_custom_binary()
    #run_all_spec2006_benchmarks()
