import random
import subprocess
import config

class MigrationPolicy:
    def __init__(self):
        pass
    

    def __setAffinity(self, pid: int, cores: set[int]) -> bool:
        affinity = ",".join([str(c) for c in cores])
        cmd_str = f"taskset -cpa {affinity} {pid}"
        command = cmd_str.split(" ")
        #print ("Executing: ", cmd_str)    
        p = subprocess.Popen(command,  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if p.stderr.readlines():
            return False
        else:
            p.wait()
            return True
        
    def executeMigration(self, currmap: dict[str, set[int]], newmap: dict[str, set[int]] , pids: dict[str, int]):
        tmp_pids = pids.copy()
        current_mapping = currmap.copy()
        #Only apply migration if the new map is different than current map
        #check each app for its new core
        for app in current_mapping:
            #if the app is still running, then move it to the new core
            #if setting the affinity fails, it means the app finished
            if pids[app] != -1:
                try:
                    self.__setAffinity(tmp_pids[app], newmap[app])
                #if the app finished, then set the pid to undefined (-1)
                except:
                    print("Migration failed. Maybe the application has not started yet.")

    # this is a no-op for the base class
    def getNewMapping(self, instructions: int, mapping: dict[str, set[int]]) -> dict[str, set[int]]:
        return mapping
    
    ##def getShuffledMapping(self, mapping):
    ##    tmp_mapping = mapping.copy()
    ##    available_cores = list(mapping.values())
    ##    random.shuffle(available_cores)
    ##    for app in mapping:
    ##        tmp_mapping[app] = available_cores.pop()
    ##    return tmp_mapping
    ##
    ##def getFixedMapping(self, mapping):
    ##    tmp_mapping = mapping.copy()
    ##    ctr = 2
    ##    for app in mapping:
    ##        tmp_mapping[app] = ctr
    ##        ctr += 2
    ##    return tmp_mapping
    ##
    ##def getRandomMapping(self, mapping):
    ##    tmp_mapping = mapping.copy()
    ##    available_cores = list(range(2, config.system_cores))
    ##    random.shuffle(available_cores)
    ##    for app in mapping:
    ##        tmp_mapping[app] = available_cores.pop()
    ##    return tmp_mapping