from config import *
from core.engine import *
from core.linuxengine import *
from core.policies.explicit_mapping import *
from core.policies.consecutive_schedule import *
from core.policies.intel_static_dvfs import *
from core.dvfs import *
from core.migration import *
from core.policies.intel_motivational_mapping import *
import time
from timeit import default_timer as timer
from random import randrange
import os




class Experiment:
    def __init__(self, name="", applications=[], mapping_policy=MappingPolicy(), scheduler=Scheduler(), dvfs_policy=DVFSPolicy(), migration_policy=None):
        self.__name = name
        self.__applications = applications
        self.__engine = Engine(self.__name, mapping_policy=mapping_policy, scheduler=scheduler, dvfs_policy=dvfs_policy, migration_policy=migration_policy)


    # Generate a random list of N unique applications to execute
    def generateRandomApps(self, N_apps):
        while len(self.__applications) < N_apps:
            candidate = available_apps[randrange(len(available_apps))]
            if candidate not in self.__applications:
                self.__applications.append(candidate)
    
    def setApplications(self, applications):
        self.__applications = applications
   
    # Execute the experiment and wait for it to finish
    def executeExperiment(self):
        self.__engine.executeWorkload(self.__applications)
    
    def __str__(self):
        return f"Experiment {self.__name} with applications {self.__applications} and engine {self.__engine}"
    
    def __repr__(self):
        return self.__str__()
    
    

class DefaultLinuxExperiment:
    def __init__(self, name="", applications=[], scheduler=Scheduler(), governor="performance", min_frequency=1500, max_frequency=3500):
        self.__name = name
        self.__applications = applications
        self.__engine = LinuxEngine(self.__name, 
                                    governor, 
                                    scheduler=scheduler, 
                                    min_frequency=min_frequency, 
                                    max_frequency=max_frequency,
                                    perf_out_file="/home/sikmoh00/Subjects/RealHardware/ARDIS/perf.out") 

    
    def setApplications(self, applications):
        self.__applications = applications
   
    # Execute the experiment and wait for it to finish
    def executeExperiment(self):
        self.__engine.executeWorkload(self.__applications)
    
    def __str__(self):
        return f"Experiment {self.__name} with applications {self.__applications} and engine {self.__engine}"
    
    def __repr__(self):
        return self.__str__()


def runExample():
   # Create an experiment object
    exp = Experiment("Simple Experiment with Specific Applications", 
                     mapping_policy=ExplicitMapping([6,19]),
                     scheduler=ConsecutiveScheduler(0),
                     dvfs_policy=DVFSPolicy({core: 3000 for core in range(system_cores)}))
    # Manually set the applications to execute
    #exp.setApplications(['parsec-fluidanimate', 'spec-omnetpp', 'spec-libquantum', 'parsec-canneal'])
    exp.setApplications(['spec-omnetpp','spec-milc'])
    # Run the experiment
    exp.executeExperiment()

def runRandomExample():
    num_random_apps = 4
    # Create an experiment object
    exp = Experiment("Simple Experiment with Random Applications")
    # Generate a random list of applications
    exp.generateRandomApps(num_random_apps)
    # Run the experiment
    exp.executeExperiment()

def runMotivationalExample():

    fixed_frequency = 2500
    motivationalDetails = {
        "total_runs": 8,
        "exp_types": [
            {
                "name": "motivECores",
                "mapping_policy": IntelMotivationalExample(),
                "dvfs_policy": DVFSPolicy({core: fixed_frequency for core in range(system_cores)})
            },
            {
                "name": "motivPCores",
                "mapping_policy": IntelMotivationalExample(False),
                "dvfs_policy": DVFSPolicy({core: fixed_frequency for core in range(system_cores)})
            }
        ],
        "applications": ['spec-omnetpp', 'spec-libquantum', 'spec-GemsFDTD', 'spec-milc', 'spec-lbm', 'spec-mcf', 'spec-bwaves', 'spec-gcc', 'spec-leslie3d'],
    }

    for exp in motivationalDetails['exp_types']:
        for exp_number in range(0, motivationalDetails['total_runs']):
            experiment = Experiment(f"{exp['name']}_{fixed_frequency}MHz_{exp_number}", mapping_policy=exp['mapping_policy'], dvfs_policy=exp['dvfs_policy'])
            experiment.setApplications(motivationalDetails['applications'][0:exp_number+1])
            print(experiment)
            experiment.executeExperiment()


def run_spec_characterization_experiments():

    scheduler=ConsecutiveScheduler(0)                   
    #for frequency in [3500, 3000, 2500, 2000, 1500]:    
    for frequency in [3500, 2500]:   
        #run on an E core
        for app in spec_apps:
            exp_name = f"{app}_{frequency}MHz_Ecore"
            if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping([intel_e_core_ids[0]]), 
                                scheduler=scheduler, 
                                dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}))
                exp.setApplications([app])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")
        #run on a P core
        for app in spec_apps:
            exp_name = f"{app}_{frequency}MHz_Pcore"
            if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping([intel_p_core_ids[3]]), 
                                scheduler=scheduler, 
                                dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}))
                exp.setApplications([app])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")

          
def run_spec_static_schedule_migration():

    scheduler=ConsecutiveScheduler(0)                    
    frequency = 2500   
    for app in spec_apps:
        exp_name = f"{app}_{frequency}MHz_Mixed"
        if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
            exp = Experiment(exp_name, 
                            mapping_policy=ExplicitMapping([intel_e_core_ids[0]]), 
                            scheduler=scheduler, 
                            dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}))
            exp.setApplications([app])
            exp.executeExperiment()
        else:
            print(f"Experiment {exp_name} already exists in the results folder.")
          
def run_parsec_static_schedule_migration():

    scheduler=ConsecutiveScheduler(0)                    
    frequency = 2500   
    for app in parsec_apps:
        exp_name = f"{app}_{frequency}MHz_Mixed"
        if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
            exp = Experiment(exp_name, 
                            mapping_policy=ExplicitMapping([intel_e_core_ids[0]]), 
                            scheduler=scheduler, 
                            dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}),
                            migration_policy=MigrationPolicy())
            exp.setApplications([app])
            exp.executeExperiment()
        else:
            print(f"Experiment {exp_name} already exists in the results folder.")  

def load_static_schedules(schedule_file):
    with open(schedule_file, 'r') as file:
        return json.load(file)

def run_parsec_static_schedule_migration_with_dvfs():

    scheduler=ConsecutiveScheduler(0)                    
    initial_frequency = 2500
    schedule_path = "/home/sikmoh00/Subjects/RealHardware/ARDIS/results/characterization_parsec/schedules/static_schedules_all_apps_with_dvfs.json"


    for app in parsec_apps:
        # Getting the starting core for the first phase of the static schedule
        static_schedule = load_static_schedules(schedule_path).get(app, [])
        initial_core_type = static_schedule[0]["core"]
        print("####   Starting core type: ", initial_core_type)
        initial_core = config.intel_e_core_ids[0] if "E-Core" in initial_core_type else config.intel_p_core_ids[3]
        exp_name = f"{app}_Mixed"
        if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
            exp = Experiment(exp_name, 
                            mapping_policy=ExplicitMapping([initial_core]), 
                            scheduler=scheduler, 
                            dvfs_policy=IntelStaticDVFSPolicy(schedule_path, {core: initial_frequency for core in range(system_cores)}),
                            migration_policy=MigrationPolicy(schedule_path))
            exp.setApplications([app])
            exp.executeExperiment()
        else:
            print(f"Experiment {exp_name} already exists in the results folder.")



def run_parsec_default_linux_governor():

    scheduler=ConsecutiveScheduler(0)      

    for governor in ["performance", "powersave", "ondemand", "conservative", "schedutil"]:
        for app in parsec_apps:
            exp_name = f"{app}_{governor}"
            if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                exp = DefaultLinuxExperiment(exp_name, 
                                scheduler=scheduler, 
                                governor=governor,
                                min_frequency=1500,
                                max_frequency=3500
                                )
                exp.setApplications([app])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")



def run_parsec_characterization_experiments():

    scheduler=ConsecutiveScheduler(0)                   
    for frequency in [3500, 3000, 2500, 2000, 1500]:    
    #for frequency in [3500,]:   
        #run on an E core
        for app in parsec_apps:
            exp_name = f"{app}_{frequency}MHz_Ecore"
            if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping([intel_e_core_ids[0]]), 
                                scheduler=scheduler, 
                                dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}))
                exp.setApplications([app])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")
        #run on a P core
        for app in parsec_apps:
            exp_name = f"{app}_{frequency}MHz_Pcore"
            if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping([intel_p_core_ids[3]]), 
                                scheduler=scheduler, 
                                dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}))
                exp.setApplications([app])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")

def run_same_application_multiple_times():
    ITERATIONS = 5
    scheduler=ConsecutiveScheduler(0)                   
    for frequency in [3500,]:     
        #run on an E core
        for app in available_apps:
            for e_core in intel_e_core_ids:
                for iteration in range(ITERATIONS):
                    exp_name = f"{app}_{frequency}MHz_Ecore_{e_core}_iter_{iteration}"
                    if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                        exp = Experiment(exp_name, 
                                        mapping_policy=ExplicitMapping([e_core]), 
                                        scheduler=scheduler, 
                                        dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}))
                        exp.setApplications([app])
                        exp.executeExperiment()
                    else:
                        print(f"Experiment {exp_name} already exists in the results folder.")
        #run on an P core
        for app in available_apps:
            for p_core in intel_p_core_ids:
                for iteration in range(ITERATIONS):
                    exp_name = f"{app}_{frequency}MHz_Pcore_{p_core}_iter_{iteration}"
                    if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                        exp = Experiment(exp_name, 
                                        mapping_policy=ExplicitMapping([p_core]), 
                                        scheduler=scheduler, 
                                        dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}))
                        exp.setApplications([app])
                        exp.executeExperiment()
                    else:
                        print(f"Experiment {exp_name} already exists in the results folder.")


if __name__ == "__main__":
    #runExample()
    #runRandomExample()
    #runMotivationalExample()
    #run_spec_characterization_experiments()
    #run_parsec_characterization_experiments()
    #run_parsec_static_schedule_migration_with_dvfs()
    run_parsec_default_linux_governor()
    #run_spec_static_schedule_migration()
    #run_parsec_static_schedule_migration()
    #run_same_application_multiple_times()