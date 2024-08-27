from config import *
from core.engine import *
from core.policies.explicit_mapping import *
from core.policies.consecutive_schedule import *
from core.dvfs import *
from core.policies.intel_motivational_mapping import *
import time
from timeit import default_timer as timer
from random import randrange
import os




class Experiment:
    def __init__(self, name="", applications=[], mapping_policy=MappingPolicy(), scheduler=Scheduler(), dvfs_policy=DVFSPolicy()):
        self.__name = name
        self.__applications = applications
        self.__engine = Engine(self.__name, mapping_policy=mapping_policy, scheduler=scheduler, dvfs_policy=dvfs_policy)


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


def run_parsec_characterization_experiments():

    scheduler=ConsecutiveScheduler(0)                   
    #for frequency in [3500, 3000, 2500, 2000, 1500]:    
    for frequency in [3500, 2500]:   
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


def run_splash2_characterization_experiments():

    scheduler=ConsecutiveScheduler(0)                   
    #for frequency in [3500, 3000, 2500, 2000, 1500]:    
    for frequency in [3500, 2500]:   
        #run on an E core
        for app in splash2_apps:
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
        for app in splash2_apps:
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
    run_splash2_characterization_experiments()
    #run_same_application_multiple_times()