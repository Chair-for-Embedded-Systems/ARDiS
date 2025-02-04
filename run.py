from config import *
from core.engine import *
from core.policies.explicit_mapping import *
from core.policies.migrate_following_schedule import *
from core.policies.dvfs_for_training import *
from core.policies.migrate_for_training import *
from core.policies.consecutive_schedule import *
from core.policies.intel_static_dvfs import *
from core.dvfs import *
from core.monitoringmode import *
from core.migration import *
from core.policies.intel_motivational_mapping import *
import time
from timeit import default_timer as timer
from random import randrange
import os




class Experiment:
    def __init__(self, name="", applications=[], mapping_policy=MappingPolicy(), scheduler=Scheduler(), dvfs_policy=DVFSPolicy(), migration_policy=None, monitoring_mode=MonitoringMode.PERIODIC_ON_CORE, results_folder=RESULTS_FOLDER):   
        self.__name = name
        self.__applications = applications
        self.__engine = Engine(self.__name, 
                       mapping_policy=mapping_policy, 
                       scheduler=scheduler, 
                       dvfs_policy=dvfs_policy, 
                       migration_policy=migration_policy, 
                       monitoring_mode=monitoring_mode,
                       results_folder=results_folder)

    # Generate a random list of N unique applications to execute
    def generateRandomApps(self, N_apps):
        while len(self.__applications) < N_apps:
            candidate = parsec_apps[randrange(len(parsec_apps))]
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
    
    

class DefaultLinuxExperiment:
    def __init__(self, name="", applications=[], scheduler=Scheduler(), governor="performance", min_frequency=1500, max_frequency=3500):
        self.__name = name
        self.__applications = applications
        self.__engine = Engine(self.__name, 
                       mapping_policy=None, 
                       scheduler=scheduler, 
                       dvfs_policy=DVFSPolicy(min_frequency=min_frequency, max_frequency=max_frequency, governor = governor), 
                       migration_policy=None, 
                       monitoring_mode=MonitoringMode.PERIODIC_ON_PID)
    
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
                     mapping_policy=ExplicitMapping([6,19]),
                     scheduler=ConsecutiveScheduler(0),
                     dvfs_policy=DVFSPolicy({core: 3000 for core in range(system_cores)}))
    # Manually set the applications to execute
    #exp.setApplications(['parsec-fluidanimate', 'spec-omnetpp', 'spec-libquantum', 'parsec-canneal'])
    exp.setApplications(['spec-omnetpp','spec-milc'])
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

    fixed_frequency = 3200

    
    for fixed_frequency in [3200, 2800, 2400, 2000]:    
        motivationalDetails = {
            "total_runs": 8,
            "exp_types": [
                {
                    "name": "motivECores",
                    "mapping_policy": IntelMotivationalExample(),
                    "scheduler": ConsecutiveScheduler(0),
                    "dvfs_policy": DVFSPolicy({core: fixed_frequency for core in range(system_cores)})
                },
                {
                    "name": "motivPCores",
                    "mapping_policy": IntelMotivationalExample(False),
                    "scheduler": ConsecutiveScheduler(0),
                    "dvfs_policy": DVFSPolicy({core: fixed_frequency for core in range(system_cores)})
                }
            ],
            "applications": ['spec-omnetpp', 'spec-libquantum', 'spec-GemsFDTD', 'spec-milc', 'spec-lbm', 'spec-mcf', 'spec-bwaves', 'spec-gcc', 'spec-leslie3d'],
        }

        for exp in motivationalDetails['exp_types']:
            for exp_number in range(0, motivationalDetails['total_runs']):
                exp_name = f"{exp['name']}_{fixed_frequency}MHz_{exp_number}"
                if not any(exp_name in folder for folder in os.listdir(MOTIVATIONAL_RESULTS_FOLDER)):
                    experiment = Experiment(
                        exp_name,
                        mapping_policy=exp['mapping_policy'],
                        dvfs_policy=exp['dvfs_policy'],
                        scheduler=exp['scheduler'],
                        monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
                        results_folder=config.MOTIVATIONAL_RESULTS_FOLDER
                        )
                    experiment.setApplications(motivationalDetails['applications'][0:exp_number+1])
                    print(experiment)
                    experiment.executeExperiment()


def run_spec_characterization_experiments():

    scheduler=ConsecutiveScheduler(0)                   
    #for frequency in [3500, 3000, 2500, 2000, 1500]:    
    for frequency in [3500, 2500]:   
        #run on an E core
        for app in spec_apps:
            exp_name = f"{app}_{frequency}MHz_Ecore"
            if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping([intel_e_core_ids[0]]), 
                                scheduler=scheduler, 
                                dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}))
                exp.setApplications([app])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")
        #run on a P core
        for app in spec_apps:
            exp_name = f"{app}_{frequency}MHz_Pcore"
            if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping([intel_p_core_ids[3]]), 
                                scheduler=scheduler, 
                                dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}))
                exp.setApplications([app])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")

          
def run_spec_static_schedule_migration():

    scheduler=ConsecutiveScheduler(0)                    
    frequency = 2500   
    for app in spec_apps:
        exp_name = f"{app}_{frequency}MHz_Mixed"
        if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
            exp = Experiment(exp_name, 
                            mapping_policy=ExplicitMapping([intel_e_core_ids[0]]), 
                            scheduler=scheduler, 
                            dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}))
            exp.setApplications([app])
            exp.executeExperiment()
        else:
            print(f"Experiment {exp_name} already exists in the results folder.")
          
def run_parsec_static_schedule_migration():

    scheduler=ConsecutiveScheduler(0)                    
    frequency = 2500   
    for app in parsec_apps:
        exp_name = f"{app}_{frequency}MHz_Mixed"
        if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
            exp = Experiment(exp_name, 
                            mapping_policy=ExplicitMapping([intel_e_core_ids[0]]), 
                            scheduler=scheduler, 
                            dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}),
                            migration_policy=StaticScheduleMigration())
            exp.setApplications([app])
            exp.executeExperiment()
        else:
            print(f"Experiment {exp_name} already exists in the results folder.")  

def load_static_schedules(schedule_file):
    with open(schedule_file, 'r') as file:
        return json.load(file)


def run_parsec_with_static_schedules():

    scheduler = ConsecutiveScheduler(0)                    
    initial_frequency = 3500
    schedule_folder = config.SCHEDULES
    parsec_apps = config.parsec_apps

    # Iterate over all schedule files in the schedule folder
    for schedule_file in os.listdir(schedule_folder):
        if schedule_file.endswith(".json"):  # Check if it's a JSON schedule file
            # Extract the part of the filename that should be included in the experiment name
            schedule_id = schedule_file.split("_")[2] + "_" + schedule_file.split("_")[3].replace(".json", "")
            schedule_path = os.path.join(schedule_folder, schedule_file)
            results_folder = os.path.join(config.RESULTS_FOLDER, f"mixed_{schedule_id}")
            if not os.path.exists(results_folder):
                os.makedirs(results_folder)

            for app in parsec_apps:
                # Getting the static schedule for the application
                static_schedule = load_static_schedules(schedule_path).get(app, [])
                initial_core = config.intel_p_core_ids[3]
                exp_name = f"{app}_Mixed_{schedule_id}"
                print(f"Running experiment {exp_name} with schedule {schedule_path}")
                if not any(exp_name in folder for folder in os.listdir(results_folder)):
                    exp = Experiment(exp_name, 
                                    mapping_policy=ExplicitMapping([initial_core]), 
                                    scheduler=scheduler, 
                                    dvfs_policy=IntelStaticDVFSPolicy(static_schedule, {core: initial_frequency for core in range(system_cores)}),
                                    migration_policy=MigrationPolicy(static_schedule),
                                    monitoring_mode=MonitoringMode.PERIODIC_ON_PID,
                                    results_folder=results_folder)
                    exp.setApplications([app])
                    exp.executeExperiment()
                else:
                    print(f"Experiment {exp_name} already exists in the results folder.")



def run_parsec_characterization_experiments_for_comparison():

    scheduler=ConsecutiveScheduler(0)                   
    for frequency in [3500,]:    
    #for frequency in [3500,]:   
        #run on an E core
        #for app in parsec_apps:
        #    exp_name = f"{app}_{frequency}MHz_Ecore"
        #    if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
        #        exp = Experiment(exp_name, 
        #                        mapping_policy=ExplicitMapping([intel_e_core_ids[0]]), 
        #                        scheduler=scheduler, 
        #                        dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}),
        #                        monitoring_mode=MonitoringMode.ONE_TIME_AT_END)
        #        exp.setApplications([app])
        #        exp.executeExperiment()
        #    else:
        #        print(f"Experiment {exp_name} already exists in the results folder.")
        #run on a P core
        #for app in ["parsec-blackscholes",]:
        for app in parsec_apps:
            exp_name = f"{app}_{frequency}MHz_Pcore"
            if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping([intel_p_core_ids[3]]), 
                                scheduler=scheduler, 
                                dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}),
                                monitoring_mode=MonitoringMode.COMBINED)
                exp.setApplications([app])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")




def run_parsec_default_linux_governor():

    scheduler=ConsecutiveScheduler(0)      

    for governor in ["performance", "powersave", "ondemand", "conservative", "schedutil"]:
        for app in parsec_apps:
            #governor = "performance"
            #app = "parsec-blackscholes"
            exp_name = f"{app}_{governor}"
            if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                exp = DefaultLinuxExperiment(exp_name, 
                                scheduler=scheduler, 
                                governor=governor,
                                min_frequency=1500,
                                max_frequency=3500
                                )
                exp.setApplications([app])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")

                
def run_parsec_characterization_experiments():

    scheduler=ConsecutiveScheduler(0)                   
    for frequency in [3500, 3400, 3300, 3200, 3100, 3000, 2900, 2800, 2700, 2600, 2500, 2400, 2300, 2200, 2100, 2000, 1900, 1800, 1700, 1600, 1500]:    
    #for frequency in [3500,]:   
        #run on a P core
        for app in parsec_apps:
            exp_name = f"{app}_{frequency}MHz_Pcore"
            if not any(exp_name in folder for folder in os.listdir(PARSEC_FIXED_FREQ_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping([intel_p_core_ids[3]]), 
                                scheduler=scheduler, 
                                dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}),
                                monitoring_mode=MonitoringMode.PERIODIC_ON_PID,
                                results_folder=config.PARSEC_FIXED_FREQ_FOLDER)
                exp.setApplications([app])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")
        #run on an E core
        for app in parsec_apps:
            exp_name = f"{app}_{frequency}MHz_Ecore"
            if not any(exp_name in folder for folder in os.listdir(PARSEC_FIXED_FREQ_FOLDER)):
                exp = Experiment(exp_name, 
                                mapping_policy=ExplicitMapping([intel_e_core_ids[0]]), 
                                scheduler=scheduler, 
                                dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}),
                                monitoring_mode=MonitoringMode.PERIODIC_ON_PID,
                                results_folder=config.PARSEC_FIXED_FREQ_FOLDER)
                exp.setApplications([app])
                exp.executeExperiment()
            else:
                print(f"Experiment {exp_name} already exists in the results folder.")

def run_same_application_multiple_times():
    ITERATIONS = 5
    scheduler=ConsecutiveScheduler(0)                   
    for frequency in [3500,]:     
        #run on an E core
        for app in available_apps:
            for e_core in intel_e_core_ids:
                for iteration in range(ITERATIONS):
                    exp_name = f"{app}_{frequency}MHz_Ecore_{e_core}_iter_{iteration}"
                    if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                        exp = Experiment(exp_name, 
                                        mapping_policy=ExplicitMapping([e_core]), 
                                        scheduler=scheduler, 
                                        dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}))
                        exp.setApplications([app])
                        exp.executeExperiment()
                    else:
                        print(f"Experiment {exp_name} already exists in the results folder.")
        #run on an P core
        for app in available_apps:
            for p_core in intel_p_core_ids:
                for iteration in range(ITERATIONS):
                    exp_name = f"{app}_{frequency}MHz_Pcore_{p_core}_iter_{iteration}"
                    if not any(exp_name in folder for folder in os.listdir(RESULTS_FOLDER)):
                        exp = Experiment(exp_name, 
                                        mapping_policy=ExplicitMapping([p_core]), 
                                        scheduler=scheduler, 
                                        dvfs_policy=DVFSPolicy({core: frequency for core in range(system_cores)}))
                        exp.setApplications([app])
                        exp.executeExperiment()
                    else:
                        print(f"Experiment {exp_name} already exists in the results folder.")


def run_training_data_experiments_with_migrations_nodfvs():
    # Number of experiments to generate
    max_applications = 15
    min_applications = 2

    # Scheduler and DVFS policy setup
    scheduler = ConsecutiveScheduler(0)
    dvfs_policy = DVFSPolicy({core: 3200 for core in range(system_cores)})  # Example fixed frequency

    # Core IDs for P-cores and E-cores
    intel_p_core_ids = config.intel_p_core_ids
    intel_e_core_ids_cluster_1 = config.intel_e_core_ids_cluster_1
    intel_e_core_ids_cluster_2 = config.intel_e_core_ids_cluster_2
    all_core_ids = intel_p_core_ids + intel_e_core_ids_cluster_1 + intel_e_core_ids_cluster_2

    experiment_target = 200
    experiment_count = 101

    while experiment_count < experiment_target:
        # Randomly choose a number of applications for this experiment
        app_count = random.randint(min_applications, max_applications)

        # Randomly select a unique set of applications for this experiment (no duplicates)
        selected_apps = random.sample(parsec_apps, app_count)  # Or spec_apps depending on the apps used

        # Generate a unique core for each application (no overlap of cores)
        random_core_mapping = {}
        available_cores = all_core_ids.copy()

        for app in selected_apps:
            core = random.choice(available_cores)
            random_core_mapping[app] = core
            available_cores.remove(core)  # Remove the core to ensure no two apps share the same core

        # Randomly choose whether to migrate within cluster or across clusters
        migrate_within_cluster = random.choice([True, False])

        # Create a unique name for this experiment
        exp_name = f"tr_exp_{app_count}apps_mig_{experiment_count}"

        # Define the experiment
        exp = Experiment(
            name=exp_name,
            mapping_policy=ExplicitMapping(list(random_core_mapping.values())),
            scheduler=scheduler,
            dvfs_policy=dvfs_policy,
            migration_policy=MigrationForTraining(migrate_within_cluster),  # Using the updated MigrationForTraining class
            monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
            results_folder=config.TRAINING_RESULTS_FOLDER  # Adjust folder path as needed
        )

        # Set the applications to the experiment
        exp.setApplications(list(random_core_mapping.keys()))

        # Print the initial mapping
        print(f"{exp_name} => Initial mapping: {random_core_mapping}")

        # Run the experiment
        exp.executeExperiment()

        experiment_count += 1

    print("Experiment complete!")
def run_training_data_experiments_with_migrations_with_dfvs():
    # Number of experiments to generate
    max_applications = 15
    min_applications = 2

    # Scheduler and DVFS policy setup
    scheduler = ConsecutiveScheduler(0)
    dvfs_policy = DVFSForTraining({core: 3200 for core in range(system_cores)})  # Example fixed frequency

    # Core IDs for P-cores and E-cores
    intel_p_core_ids = config.intel_p_core_ids
    intel_e_core_ids_cluster_1 = config.intel_e_core_ids_cluster_1
    intel_e_core_ids_cluster_2 = config.intel_e_core_ids_cluster_2
    all_core_ids = intel_p_core_ids + intel_e_core_ids_cluster_1 + intel_e_core_ids_cluster_2

    experiment_target = 500
    experiment_count = 188

    while experiment_count < experiment_target:
        # Randomly choose a number of applications for this experiment
        app_count = random.randint(min_applications, max_applications)

        # Randomly select a unique set of applications for this experiment (no duplicates)
        selected_apps = random.sample(parsec_apps, app_count)  # Or spec_apps depending on the apps used

        # Generate a unique core for each application (no overlap of cores)
        random_core_mapping = {}
        available_cores = all_core_ids.copy()

        for app in selected_apps:
            core = random.choice(available_cores)
            random_core_mapping[app] = core
            available_cores.remove(core)  # Remove the core to ensure no two apps share the same core

        # Randomly choose whether to migrate within cluster or across clusters
        migrate_within_cluster = random.choice([True, False])

        # Create a unique name for this experiment
        exp_name = f"tr_exp_{app_count}apps_mig_{experiment_count}"

        # Define the experiment
        exp = Experiment(
            name=exp_name,
            mapping_policy=ExplicitMapping(list(random_core_mapping.values())),
            scheduler=scheduler,
            dvfs_policy=dvfs_policy,
            migration_policy=MigrationForTraining(migrate_within_cluster),  # Using the updated MigrationForTraining class
            monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
            results_folder=config.TRAINING_RESULTS_FOLDER  # Adjust folder path as needed
        )

        # Set the applications to the experiment
        exp.setApplications(list(random_core_mapping.keys()))

        # Print the initial mapping
        print(f"{exp_name} => Initial mapping: {random_core_mapping}")

        # Run the experiment
        exp.executeExperiment()

        experiment_count += 1

    print("Experiment complete!")


def run_experiment_with_ml_predictions():
    # Number of experiments to generate
    max_applications = 15
    min_applications = 2

    # Scheduler and DVFS policy setup
    scheduler = ConsecutiveScheduler(0)
    dvfs_policy = DVFSForTraining({core: 3200 for core in range(system_cores)})  # Example fixed frequency

    # Core IDs for P-cores and E-cores
    intel_p_core_ids = config.intel_p_core_ids
    intel_e_core_ids_cluster_1 = config.intel_e_core_ids_cluster_1
    intel_e_core_ids_cluster_2 = config.intel_e_core_ids_cluster_2
    all_core_ids = intel_p_core_ids + intel_e_core_ids_cluster_1 + intel_e_core_ids_cluster_2

    experiment_target = 500
    experiment_count = 0

    while experiment_count < experiment_target:
        # Randomly choose a number of applications for this experiment
        app_count = random.randint(min_applications, max_applications)

        # Randomly select a unique set of applications for this experiment (no duplicates)
        selected_apps = random.sample(parsec_apps, app_count)  # Or spec_apps depending on the apps used

        # Generate a unique core for each application (no overlap of cores)
        random_core_mapping = {}
        available_cores = all_core_ids.copy()

        for app in selected_apps:
            core = random.choice(available_cores)
            random_core_mapping[app] = core
            available_cores.remove(core)  # Remove the core to ensure no two apps share the same core

        # Randomly choose whether to migrate within cluster or across clusters
        migrate_within_cluster = random.choice([True, False])

        # Create a unique name for this experiment
        exp_name = f"tr_exp_{app_count}apps_mig_{experiment_count}"

        # Define the experiment
        exp = Experiment(
            name=exp_name,
            mapping_policy=ExplicitMapping(list(random_core_mapping.values())),
            scheduler=scheduler,
            dvfs_policy=dvfs_policy,
            migration_policy=MigrationForTraining(migrate_within_cluster),  # Using the updated MigrationForTraining class
            monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
            results_folder=config.EVALUATION_FOLDER  # Adjust folder path as needed
        )

        # Set the applications to the experiment
        exp.setApplications(list(random_core_mapping.keys()))

        # Print the initial mapping
        print(f"{exp_name} => Initial mapping: {random_core_mapping}")

        # Run the experiment
        exp.executeExperiment()

        experiment_count += 1

    print("Experiment complete!")


def run_training_data_experiments_without_migrations():
    # Number of experiments to generate
    max_applications = 15
    min_applications = 2

    # Scheduler and DVFS policy setup
    scheduler = ConsecutiveScheduler(0)
    dvfs_policy = DVFSPolicy({core: 3200 for core in range(system_cores)})  # Example fixed frequency

    # Core IDs for P-cores and E-cores
    intel_p_core_ids = config.intel_p_core_ids
    intel_e_core_ids_cluster_1 = config.intel_e_core_ids_cluster_1
    intel_e_core_ids_cluster_2 = config.intel_e_core_ids_cluster_2
    all_core_ids = intel_p_core_ids + intel_e_core_ids_cluster_1 + intel_e_core_ids_cluster_2

    experiment_target = 200
    experiment_count = 101

    while experiment_count < experiment_target:
        # Randomly choose a number of applications for this experiment
        app_count = random.randint(min_applications, max_applications)

        # Randomly select a unique set of applications for this experiment (no duplicates)
        selected_apps = random.sample(parsec_apps, app_count)  # Or spec_apps depending on the apps used

        # Generate a unique core for each application (no overlap of cores)
        random_core_mapping = {}
        available_cores = all_core_ids.copy()

        for app in selected_apps:
            core = random.choice(available_cores)
            random_core_mapping[app] = core
            available_cores.remove(core)  # Remove the core to ensure no two apps share the same core

        # Randomly choose whether to migrate within cluster or across clusters
        migrate_within_cluster = random.choice([True, False])

        # Create a unique name for this experiment
        exp_name = f"tr_exp_{app_count}apps_nomig_{experiment_count}"

        # Define the experiment
        exp = Experiment(
            name=exp_name,
            mapping_policy=ExplicitMapping(list(random_core_mapping.values())),
            scheduler=scheduler,
            dvfs_policy=dvfs_policy,
            migration_policy=None,
            monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
            results_folder=config.TRAINING_RESULTS_FOLDER  # Adjust folder path as needed
        )

        # Set the applications to the experiment
        exp.setApplications(list(random_core_mapping.keys()))

        # Print the initial mapping
        print(f"{exp_name} => Initial mapping: {random_core_mapping}")

        # Run the experiment
        exp.executeExperiment()

        experiment_count += 1

    print("Experiment complete!")

def run_aoi_with_background_experiments():
    # Parameters
    max_background_apps = 14
    min_background_apps = 1

    # Scheduler setup
    scheduler = ConsecutiveScheduler(0)

    # Core IDs for P-cores and E-cores
    intel_p_core_ids = config.intel_p_core_ids
    intel_e_core_ids_cluster_1 = config.intel_e_core_ids_cluster_1
    intel_e_core_ids_cluster_2 = config.intel_e_core_ids_cluster_2
    all_core_ids = intel_p_core_ids + intel_e_core_ids_cluster_1 + intel_e_core_ids_cluster_2
    e_cores = intel_e_core_ids_cluster_1 + intel_e_core_ids_cluster_2

    # Experiment limits
    experiment_target = 1000
    experiment_count = 174

    # Loop until reaching the target number of experiments
    while experiment_count < experiment_target:
        # Select an application of interest (AOI)
        aoi = random.choice(parsec_apps)  # Replace parsec_apps with the actual AOI list if different

        # Randomly choose a number of background applications
        background_app_count = random.randint(min_background_apps, max_background_apps)

        # Select a unique set of background applications (no duplicates with AOI)
        background_apps = random.sample([app for app in parsec_apps if app != aoi], background_app_count)

        # Generate two experiments: AOI mapped to a P-core and AOI mapped to an E-core
        for core_type, core_id_list in {"p_core": intel_p_core_ids, "e_core": e_cores}.items():
            # Ensure there are available cores to map background apps
            if len(background_apps) + 1 > len(all_core_ids):
                print("Not enough cores for this setup.")
                continue

            # Core mapping
            random_core_mapping = {}
            available_cores = all_core_ids.copy()

            # Map AOI to a specific core type (P-core or E-core)
            aoi_core = random.choice(core_id_list)
            random_core_mapping[aoi] = aoi_core
            available_cores.remove(aoi_core)

            # Map background applications to the remaining cores randomly
            for app in background_apps:
                core = random.choice(available_cores)
                random_core_mapping[app] = core
                available_cores.remove(core)  # Ensure no two apps share the same core

            # Randomly select a frequency from 1800 to 3200 in steps of 200
            frequency = random.choice(range(1800, 3201, 200))
            dvfs_policy = DVFSPolicy({core: frequency for core in range(system_cores)})

            # Construct a codified name for the background applications
            bg_apps_code = "".join([app[7:9] for app in background_apps])

            # Experiment name to reflect AOI, background applications, core type, and frequency
            exp_name = f"tr_exp_{aoi.replace('parsec-','')}_bg_{bg_apps_code}_{core_type}_{experiment_count}"
            print(f"Experiment {exp_name} at {frequency} MHz")
            
            # Define the experiment with a frequency-specific results folder
            results_folder = f"{config.MOTIVATIONAL_RESULTS_FOLDER}/{frequency}MHz"
            exp = Experiment(
                name=exp_name,
                mapping_policy=ExplicitMapping(list(random_core_mapping.values())),
                scheduler=scheduler,
                dvfs_policy=dvfs_policy,
                migration_policy=None,
                monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
                results_folder=results_folder
            )

            # Set the applications to the experiment
            exp.setApplications(list(random_core_mapping.keys()))

            # Print the initial mapping
            print(f"{exp_name} => Initial mapping: {random_core_mapping}")

            # Run the experiment
            exp.executeExperiment()
            
            experiment_count += 1
            
    print("Experiment complete!")

def run_overhead_analysis_without_monitoring():
    # Number of experiments to generate
    num_applications = 16
    scheduler = ConsecutiveScheduler(0)

    intel_p_core_ids = config.intel_p_core_ids
    intel_e_core_ids_cluster_1 = config.intel_e_core_ids_cluster_1
    intel_e_core_ids_cluster_2 = config.intel_e_core_ids_cluster_2
    all_core_ids = intel_p_core_ids + intel_e_core_ids_cluster_1 + intel_e_core_ids_cluster_2
    print(all_core_ids)
    experiment_target = 15
    experiment_count = 1

    while experiment_count < experiment_target:
        # Randomly choose a number of applications for this experiment

        # Randomly select a unique set of applications for this experiment (no duplicates)
        selected_apps = random.sample(config.spec_apps, num_applications)  # Or spec_apps depending on the apps used

        # Generate a unique core for each application (no overlap of cores)
        random_core_mapping = {}
        available_cores = all_core_ids.copy()

        for app in selected_apps:
            core = random.choice(available_cores)
            random_core_mapping[app] = core
            available_cores.remove(core)  # Remove the core to ensure no two apps share the same core

        # Create a unique name for this experiment
        exp_name = f"exp_{num_applications}apps_mig_{experiment_count}_without_monitoring"

        # Define the experiment
        exp = Experiment(
            name=exp_name,
            mapping_policy=ExplicitMapping(list(random_core_mapping.values())),
            scheduler=scheduler,
            dvfs_policy=None,
            migration_policy=None,  # Using the updated MigrationForTraining class
            monitoring_mode=MonitoringMode.OFF,
            results_folder=config.OVERHEAD_RESULTS_FOLDER  # Adjust folder path as needed
        )

        # Set the applications to the experiment
        exp.setApplications(list(random_core_mapping.keys()))

        # Run the experiment
        exp.executeExperiment()

        experiment_count += 1

    print("Experiment complete!")



def run_overhead_analysis():
    # Number of experiments to generate
    num_applications = 16
    scheduler = ConsecutiveScheduler(0)

    intel_p_core_ids = config.intel_p_core_ids
    intel_e_core_ids_cluster_1 = config.intel_e_core_ids_cluster_1
    intel_e_core_ids_cluster_2 = config.intel_e_core_ids_cluster_2
    all_core_ids = intel_p_core_ids + intel_e_core_ids_cluster_1 + intel_e_core_ids_cluster_2
    print(all_core_ids)
    experiment_target = 15
    experiment_count = 1


    experiment_target = 30
    experiment_count = 7

    while experiment_count < experiment_target:
        # Randomly choose a number of applications for this experiment

        # Randomly select a unique set of applications for this experiment (no duplicates)
        selected_apps = random.sample(config.spec_apps, num_applications)  # Or spec_apps depending on the apps used

        # Generate a unique core for each application (no overlap of cores)
        random_core_mapping = {}
        available_cores = all_core_ids.copy()

        for app in selected_apps:
            core = random.choice(available_cores)
            random_core_mapping[app] = core
            available_cores.remove(core)  # Remove the core to ensure no two apps share the same core

        # Create a unique name for this experiment
        exp_name = f"exp_{num_applications}apps_mig_{experiment_count}_with_monitoring"

        # Define the experiment
        exp = Experiment(
            name=exp_name,
            mapping_policy=ExplicitMapping(list(random_core_mapping.values())),
            scheduler=scheduler,
            dvfs_policy=DVFSPolicy({core: 3200 for core in range(system_cores)}),
            migration_policy=None,  # Using the updated MigrationForTraining class
            monitoring_mode=MonitoringMode.PERIODIC_ON_CORE,
            results_folder=config.OVERHEAD_RESULTS_FOLDER  # Adjust folder path as needed
        )

        # Set the applications to the experiment
        exp.setApplications(list(random_core_mapping.keys()))

        # Run the experiment
        exp.executeExperiment()

        # Create a unique name for this experiment
        exp_name2 = f"exp_{num_applications}apps_mig_{experiment_count}_without_monitoring"

        # Define the experiment
        exp2 = Experiment(
            name=exp_name2,
            mapping_policy=ExplicitMapping(list(random_core_mapping.values())),
            scheduler=scheduler,
            dvfs_policy=None,
            migration_policy=None,  # Using the updated MigrationForTraining class
            monitoring_mode=MonitoringMode.OFF,
            results_folder=config.OVERHEAD_RESULTS_FOLDER  # Adjust folder path as needed
        )

        # Set the applications to the experiment
        exp2.setApplications(list(random_core_mapping.keys()))

        # Run the experiment
        exp2.executeExperiment()

        experiment_count += 1
    print("Experiment complete!")


if __name__ == "__main__":
    #runExample()
    #runRandomExample()
    #runMotivationalExample()
    #run_training_data_experiments_with_migrations_nodfvs()
    #run_training_data_experiments_with_migrations_with_dfvs()
    #run_training_data_experiments_without_migrations()
    #run_aoi_with_background_experiments()
    #run_overhead_analysis()
    #run_overhead_analysis_without_monitoring()
    run_experiment_with_ml_predictions()