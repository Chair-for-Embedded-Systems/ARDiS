from config import *
from core.engine import *
from core.policies.explicit_mapping import *
from core.policies.consecutive_schedule import *
from core.dvfs import *
from core.policies.intel_motivational_mapping import *
import time
from timeit import default_timer as timer
from random import randrange




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
                     mapping_policy=ExplicitMapping([4,17, 2, 6]),
                     scheduler=ConsecutiveScheduler(5),
                     dvfs_policy=DVFSPolicy())
    # Manually set the applications to execute
    exp.setApplications(['parsec-fluidanimate', 'spec-omnetpp', 'spec-libquantum', 'parsec-canneal'])
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


if __name__ == "__main__":
    #runExample()
    #runRandomExample()
    runMotivationalExample()