from config import *
from core.engine import *
from core.scheduler import *
from core.policies.consecutive_schedule import *
from core.dvfs import *
from core.policies.intel_motivational_mapping import *
import time
from timeit import default_timer as timer
from random import randrange




class Experiment:
    def __init__(self, name="", applications=[]):
        self.__name = name
        self.__applications = applications
        self.__engine = Engine(self.__name, IntelMotivationalExample(False))
        #self.__scheduler = Scheduler()
        # Create a schedule with a delay in the arrival time of 2.5 seconds between each application
        # use 0 for all applications to arrive at the same time
        self.__scheduler = ConsecutiveScheduler(2.5)

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
        self.__scheduler.createSchedule(self.__applications)
        #TODO: for now we are passing the schedule to the engine
        # if we want a periodic schedule policy we need to pass the scheduler to the engine, probably
        self.__engine.executeWorkload(self.__applications, self.__scheduler.schedule)
    
    def setInitialFrequency(self, frequency):
        self.__engine.setStaticFrequency(frequency)


def runExample():
   # Create an experiment object
    exp = Experiment("Simple Experiment with Specific Applications")
    # Manually set the applications to execute
    exp.setApplications(['parsec-ferret', 'parsec-canneal', 'parsec-streamcluster', 'parsec-freqmine'])
    # Set the initial frequency of the cores
    exp.setInitialFrequency(2900)
    # Run the experiment
    exp.executeExperiment()


def runRandomExample():
    # Create an experiment object
    exp = Experiment("Simple Experiment with Random Applications")
    # Generate a random list of applications
    exp.generateRandomApps(system_cores)
    # Set the initial frequency of the cores
    exp.setInitialFrequency(2900)
    # Run the experiment
    exp.executeExperiment()

def runMotivationalExample():
    exp = Experiment("Motivational Example")
    exp.setApplications(['parsec-ferret', 'parsec-canneal', 'parsec-streamcluster', 'parsec-freqmine'])
    exp.setInitialFrequency(2900)
    exp.executeExperiment()

if __name__ == "__main__":
    #runExample()
    #runRandomExample()
    runMotivationalExample()




    



