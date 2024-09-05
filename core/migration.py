import threading
import subprocess
import random
import config
import json



class MigrationPolicy:
    def __init__(self, static_schedule_path):
        self.static_schedules = self.load_static_schedules(static_schedule_path)
    
    def load_static_schedules(self, schedule_file):
        with open(schedule_file, 'r') as file:
            return json.load(file)

    def __setAffinity(self, pid, core):
        cmd_str = "taskset -cp " + str(core) + " " + str(pid)
        command = cmd_str.split(" ")
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
        #check each app for its new core
        for app in currmap:
            #if the app is still running, then move it to the new core
            #if setting the affinity fails, it means the app finished
            if pids[app] != -1:
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
    
    def getFixedMapping(self, mapping):
        tmp_mapping = mapping.copy()
        ctr = 2
        for app in mapping:
            tmp_mapping[app] = ctr
            ctr += 2
        return tmp_mapping
    
    def getRandomMapping(self, mapping):
        tmp_mapping = mapping.copy()
        available_cores = list(range(2, config.system_cores))
        random.shuffle(available_cores)
        for app in mapping:
            tmp_mapping[app] = available_cores.pop()
        return tmp_mapping
    

    def getStaticScheduleMapping(self, instructions, mapping):
        tmp_mapping = mapping.copy()
        for app in tmp_mapping:
            static_schedule = self.static_schedules.get(app, [])
            selected_core = tmp_mapping[list(tmp_mapping.keys())[0]]  # Default to current core
            current_phase = None
            for entry in static_schedule:
                if instructions >= entry["trigger_instruction"]:
                    selected_core = config.intel_e_core_ids[0] if "E-core" in entry["core"] else config.intel_p_core_ids[3]
                    current_phase = entry["phase"]
                else:
                    break  # Stop once the correct phase is determined

            if tmp_mapping[app] != selected_core:
                tmp_mapping[app] = selected_core
                print("[Migration Policy] Now entering Phase: ", current_phase, "Core: ", selected_core)
        
        return tmp_mapping



# # Let's test the migration policy
# migration = MigrationPolicy()
# mapping  = {"app1": 0, "app2": 2, "app3": 4, "app4": 6, "app5": 8, "app6": 10}
# pids = {"app1": 100, "app2": 200, "app3": 300, "app4": 400, "app5": 500, "app6": 600}
# newmapping = migration.getShuffledMapping(mapping)
# print("original map is", mapping)
# print("new map is", newmapping)
# print(migration.executeMigration(mapping, newmapping, pids))
