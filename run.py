from config import *
from core.engine import *
import time
from timeit import default_timer as timer
from random import randrange


engine = Engine()

# Generate a random mapping of unique applications to cores
def generateRandomApps():
    apps = []
    while len(apps) < system_cores:
        candidate = available_apps[randrange(len(available_apps))]
        if candidate not in apps:
            apps.append(candidate)
    return apps



def run_simple(base_map, workdir=None):
    print("Running workload with mapping: ", base_map)
    # Execute the workload
    engine.executeWorkload(base_map) 
    print("Experiment finished sucessfully!")

if __name__ == "__main__":
    premaps = []

    for x in range(num_workloads):
       premaps.append(generateRandomApps())

    for idx in range(len(premaps)):
        print("Running workload ", idx + 1)
        run_simple(premaps[idx])
        print("Workload ", idx + 1, " finished")
    


    



