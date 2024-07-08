from config import *
from core.engine import *
from core.scheduler import *
import time
from timeit import default_timer as timer
from random import randrange




class Experiment:
    def __init__(self, name="", applications=[]):
        self.__name = name
        self.__applications = applications
        self.__engine = Engine()
        self.__scheduler = Scheduler()

    # Generate a random list of N unique applications to execute
    def generateRandomApps(self, N_apps):
        while len(self.__applications) < N_apps:
            candidate = available_apps[randrange(len(available_apps))]
            if candidate not in self.__applications:
                self.__applications.append(candidate)
   
    # Execute the experiment and wait for it to finish
    def executeExperiment(self):
        self.__scheduler.createSchedule(self.__applications)
        #TODO: for now we are passing the schedule to the engine
        # if we want a periodic schedule policy we need to pass the scheduler to the engine, probably
        self.__engine.executeWorkload(self.__applications, self.__scheduler.schedule)



if __name__ == "__main__":
    # Create an experiment object
    exp = Experiment("Simple Experiment")
    # Generate a random list of workloads
    exp.generateRandomApps(4)
    # Run the experiment
    exp.executeExperiment()




    



