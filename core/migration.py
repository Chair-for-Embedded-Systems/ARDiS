import threading
import subprocess
import random
import config



class MigrationPolicy:
    def __init__(self, params = {}):
        self.params = params
    
    def __setAffinity(self, pid, core):
        cmd_str = "taskset -cp " + str(core) + " " + str(pid)
        command = cmd_str.split(" ")
        if DEBUG:
            print ("Executing: ", cmd_str)    
        p = subprocess.Popen(command,  stderr=subprocess.PIPE, stdout=subprocess.PIPE)
        if p.stderr.readlines():
            return False
        else:
            p.wait()
            return True
        
    def executeMigration(self, currmap , newmap , pids):
        tmp_pids = pids.copy()
        #Only apply migration if the new map is different than current map
        if (newmap != currmap):
            #check each app for its new core
            for app in currmap:
                if currmap[app] != newmap[app]:
                    #if the app is still running, then move it to the new core
                    #if setting the affinity fails, it means the app finished
                    try:
                        self.__setAffinity(pids[app], newmap[app])
                        tmp_pids[app] = pids[app]
                    #if the app finished, then set the pid to undefined (-1)
                    except:
                        tmp_pids[app] = -1
                    
        return tmp_pids
    
    def getShuffledMapping(self, mapping):
        tmp_mapping = mapping.copy()
        available_cores = list(mapping.values())
        random.shuffle(available_cores)
        for app in mapping:
            tmp_mapping[app] = available_cores.pop()
        return tmp_mapping


# # Let's test the migration policy
# migration = MigrationPolicy()
# mapping  = {"app1": 0, "app2": 2, "app3": 4, "app4": 6, "app5": 8, "app6": 10}
# pids = {"app1": 100, "app2": 200, "app3": 300, "app4": 400, "app5": 500, "app6": 600}
# newmapping = migration.getShuffledMapping(mapping)
# print("original map is", mapping)
# print("new map is", newmapping)
# print(migration.executeMigration(mapping, newmapping, pids))
