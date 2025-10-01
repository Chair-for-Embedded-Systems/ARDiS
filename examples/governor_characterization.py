import os

from ardis.benchmarks import ParsecApplication
import ardis.config as config

from ardis.core import *
from ardis.core.policies import ExplicitMapping, ConsecutiveScheduler
from ardis.experiments import DefaultLinuxExperiment

def run_parsec_default_linux_governor():

    scheduler=ConsecutiveScheduler(0)      

    for governor in ["performance", "powersave", "ondemand", "conservative", "schedutil"]:
        for app in config.parsec_apps:
            #governor = "performance"
            #app = "parsec-blackscholes"
            exp_name = f"{app}_{governor}"
            if not any(exp_name in folder for folder in os.listdir(config.RESULTS_FOLDER)):
                exp = DefaultLinuxExperiment(exp_name, 
                                scheduler=scheduler, 
                                governor=governor,
                                min_frequency_mhz=1500,
                                max_frequency_mhz=3500,
                                monitoring_mode=MonitoringMode.PERIODIC_ON_CORE)
                                
                exp.setApplications([ParsecApplication(app)])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")

def run_parsec_default_linux_governor_simple():

    scheduler=ConsecutiveScheduler(0)      
    governor = "performance"
    app = ParsecApplication("splash2x.radix")
    exp_name = f"{app}_{governor}"
    exp = DefaultLinuxExperiment(exp_name, 
                    scheduler=scheduler,
                    mapping_policy=ExplicitMapping.from_list([6, 19]),
                    governor=governor,
                    min_frequency_mhz=1500,
                    max_frequency_mhz=3500,
                    monitoring_mode=MonitoringMode.PERIODIC_ON_PID)
                    
    exp.setApplications([app])
    exp.executeExperiment()

                

if __name__ == "__main__":
    run_parsec_default_linux_governor_simple()
    run_parsec_default_linux_governor()