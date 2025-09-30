import os

from ardis.benchmarks import ParsecApplication
import ardis.config as config

from ardis.core import *
from ardis.core.policies import ExplicitMapping, ConsecutiveScheduler, StaticDVFS
from ardis.experiments import Experiment

def run_parsec_characterization_experiments():

    scheduler=ConsecutiveScheduler(0)                   
    for frequency in [3500, 3400, 3300, 3200, 3100, 3000, 2900, 2800, 2700, 2600, 2500, 2400, 2300, 2200, 2100, 2000, 1900, 1800, 1700, 1600, 1500]:    
        #run on a P core
        for app in config.parsec_apps:
            exp_name = f"{app}_{frequency}MHz_Pcore"
            if not any(exp_name in folder for folder in os.listdir(config.RESULTS_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping.from_list([config.intel_p_core_ids[3]]), 
                                scheduler=scheduler, 
                                dvfs_policy=StaticDVFS({core: frequency for core in range(config.system_cores)}),
                                monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
                                results_folder=config.RESULTS_FOLDER)
                exp.setApplications([ParsecApplication(app)])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")
        #run on an E core
        for app in config.parsec_apps:
            exp_name = f"{app}_{frequency}MHz_Ecore"
            if not any(exp_name in folder for folder in os.listdir(config.RESULTS_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping.from_list([config.intel_e_core_ids[0]]), 
                                scheduler=scheduler, 
                                dvfs_policy=StaticDVFS({core: frequency for core in range(config.system_cores)}),
                                monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
                                results_folder=config.RESULTS_FOLDER)
                exp.setApplications([ParsecApplication(app)])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")

if __name__ == "__main__":
    run_parsec_characterization_experiments()