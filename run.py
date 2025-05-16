from config import *
from core.engine import *
from core.policies.explicit_mapping import *
from core.policies.migrate_following_schedule import *
from core.policies.dvfs_for_training import *
from core.policies.migrate_for_training import *
from core.policies.consecutive_schedule import *
from core.policies.intel_static_dvfs import *
from core.dvfs import *
from core.monitoringmode import *
from core.migration import *
from core.policies.intel_motivational_mapping import *
from core.postprocessing.result_plotter import ResultPlotter, BasicResultPlotter, Diagrams
import time
from timeit import default_timer as timer
from random import randrange
import os




class Experiment:
    def __init__(self, name="", applications: list[str] = [], mapping_policy=MappingPolicy(), scheduler=Scheduler(), dvfs_policy=DVFSPolicy(), migration_policy=None, monitoring_mode=MonitoringMode.PERIODIC_ON_CORE, results_folder=RESULTS_FOLDER):   
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
                self.__applications.append(candidate)
    
    def setApplications(self, applications):
        self.__applications = applications
   
    # Execute the experiment and wait for it to finish
    def executeExperiment(self):
        self.__engine.executeWorkload(self.__applications)
    
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
                       dvfs_policy=DVFSPolicy(min_frequency=min_frequency, max_frequency=max_frequency, governor = governor), 
                       migration_policy=None, 
                       monitoring_mode=monitoring_mode)
    
    def setApplications(self, applications):
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
                     dvfs_policy=DVFSPolicy({core: 3000 for core in range(system_cores)}),
                     monitoring_mode=MonitoringMode.PERIODIC_ON_CORE)
    # Manually set the applications to execute
    exp.setApplications(['parsec-blackscholes', 'parsec-splash2x.radix', 'parsec-bodytrack'])
    # Run the experiment
    exp.executeExperiment()

def run_example_with_PID_monitoring():
   # Create an experiment object
    exp = Experiment("Simple Experiment with Specific Applications", 
                     mapping_policy=ExplicitMapping.from_list([6, 19]),
                     scheduler=ConsecutiveScheduler(0),
                     dvfs_policy=DVFSPolicy({core: 3000 for core in range(system_cores)}),
                     monitoring_mode=MonitoringMode.PERIODIC_ON_PID)
    # Manually set the applications to execute
    exp.setApplications(['parsec-blackscholes'])
    # Run the experiment
    exp.executeExperiment()


def run_parsec_default_linux_governor_simple():

    scheduler=ConsecutiveScheduler(0)      
    governor = "performance"
    app = "parsec-splash2x.radix"
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
                                
                exp.setApplications([app])
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
                                dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}),
                                monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
                                results_folder=config.RESULTS_FOLDER)
                exp.setApplications([app])
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
                                dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}),
                                monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
                                results_folder=config.RESULTS_FOLDER)
                exp.setApplications([app])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")


def run_example_with_result_plotting():
    
    exp = Experiment("Experiment with result plotting", 
                     mapping_policy=ExplicitMapping.from_list([3, 6, 19]),
                     scheduler=ConsecutiveScheduler(0),
                     dvfs_policy=DVFSPolicy({core: 3000 for core in range(system_cores)}),
                     monitoring_mode=MonitoringMode.PERIODIC_ON_PID)
    
    exp.setApplications(['parsec-blackscholes', 'parsec-splash2x.radix', 'parsec-bodytrack'])
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
        applications=["parsec-dedup", "parsec-splash2x.radix"],
        mapping_policy=ExplicitMapping([{2, 4, 6, 8}, {16}]),
        scheduler=ConsecutiveScheduler(0),
        dvfs_policy=DVFSPolicy({core: 3500 for core in range(system_cores)}),
        monitoring_mode=MonitoringMode.PERIODIC_ON_TID
    )
    exp.executeExperiment()
    rp = BasicResultPlotter(
        experiment_folder=exp.getWorkingDirectory(),
        diagrams=[Diagrams.EXECUTION_OVERVIEW, Diagrams.INSTRUCTIONS, Diagrams.MAPPING, Diagrams.FREQUENCY]
    )
    rp.plot_results(verbose=True)

if __name__ == "__main__":
    #run_example_with_core_monitoring()
    #run_example_with_PID_monitoring()
    #run_parsec_default_linux_governor()
    #run_parsec_characterization_experiments()
    #run_example_with_result_plotting()
    run_example_with_TID_monitoring()

