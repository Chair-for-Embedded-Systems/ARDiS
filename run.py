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
    # Start the workload
    engine.startWorkload(base_map) 
    # Get the PIDs of the applications
    pids = engine.getProcessIds()
    print("PIDs: ", pids)

    while engine.running:
        # print the current mapping every 5 seconds
        if (int(engine.getElapsedTime()) % 5 == 0):
            print("Current map:", engine.mapping)
            time.sleep(1)
        time.sleep(0.1)

    print("Experiment finished sucessfully!")

if __name__ == "__main__":
    premaps = []

    for x in range(num_workloads):
       premaps.append(generateRandomApps())

    for idx in range(len(premaps)):
        print("Running workload ", idx + 1)
        run_simple(premaps[idx])
        print("Workload ", idx, " finished")
    


    



