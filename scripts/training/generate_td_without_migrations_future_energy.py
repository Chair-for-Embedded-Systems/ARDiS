'''
    This script is used to parse the results from experiments with static mapping and static frequencies.
    To get the IPC and Energy from the next epoch.
'''

import os
import re
import pandas as pd

import sys
import numpy as np
# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
from ardis.config import *


# Map each core to its cluster type
core_to_cluster = {core: 'P' for core in intel_p_core_ids}
core_to_cluster.update({core: 'E1' for core in intel_e_core_ids_cluster_1})
core_to_cluster.update({core: 'E2' for core in intel_e_core_ids_cluster_2})

def parse_log_file(filepath):
    """Parses periodic_counters.log and returns a structured list of epochs."""
    epochs = []
    with open(filepath, 'r') as file:
        current_epoch = {}
        for line in file:
            if 'Current mapped cores' in line:
                # Start of a new epoch
                if current_epoch:
                    epochs.append(current_epoch)
                current_epoch = {'cores': {}}
            elif 'Core' in line:
                core_data = parse_core_line(line)
                core_id = core_data['core']
                current_epoch['cores'][core_id] = core_data
            elif 'SYSTEM' in line:
                current_epoch['system'] = parse_system_line(line)
        if current_epoch:
            epochs.append(current_epoch)
    return epochs

def parse_core_line(line):
    """Extracts core information from a log line."""
    core_info = {}
    core_id = int(re.search(r'Core (\d+):', line).group(1))
    app_name = re.search(r'app = (.*?) \|', line).group(1)
    core_info['core'] = core_id
    core_info['app'] = app_name
    core_info['cluster'] = core_to_cluster.get(core_id, 'Unknown')
    
    # Update regex to support multiple hyphens in metric names
    core_info.update({k: int(v) for k, v in re.findall(r'([\w-]+) = (\d+)', line)})
    
    #print(core_info)  # For debugging to confirm it works as expected
    return core_info

def parse_system_line(line):
    """Extracts system-wide information from a log line."""
    return {k: float(v) for k, v in re.findall(r'(\w+/energy-\w+/) = ([\d.]+)', line)}

def create_dataset(epochs, frequency, log_path):
    """Creates a DataFrame from parsed epochs with AOI-based structure."""
    data_rows = []
    
    path_date_time = log_path.split("_")[0] + "_" + log_path.split("_")[1]
    path_date_time = path_date_time.replace("-", "")
    for i, epoch in enumerate(epochs):
        #print(epoch)  # For debugging, to see the structure of each epoch
        
        if i+1 < len(epochs) and "system" in epoch and "system" in epochs[i+1]:
            for aoicore, aoidata in epoch['cores'].items():
                aoi_cluster = aoidata['cluster']
                #print(aoidata)
                # Determine the other two clusters based on the AOI cluster
                if aoi_cluster == 'P':
                    other1_cluster, other2_cluster = 'E1', 'E2'
                elif aoi_cluster == 'E1':
                    other1_cluster, other2_cluster = 'P', 'E2'
                elif aoi_cluster == 'E2':
                    other1_cluster, other2_cluster = 'P', 'E1'
                else:
                    continue  # Skip if the cluster is not recognized

                # Separate applications based on the determined clusters
                same_cluster_apps = {c: d for c, d in epoch['cores'].items() if d['cluster'] == aoi_cluster and c != aoicore}
                other1_apps = {c: d for c, d in epoch['cores'].items() if d['cluster'] == other1_cluster}
                other2_apps = {c: d for c, d in epoch['cores'].items() if d['cluster'] == other2_cluster}

                # Look ahead to next epoch for AOI IPC if the same application is running
                next_epoch_system_data = epochs[i+1]['system'] if i+1 < len(epochs) else None
                next_epoch_data = epochs[i+1]['cores'].get(aoicore) if i+1 < len(epochs) else None
                next_epoch_ipc = (
                    next_epoch_data['instructions'] / next_epoch_data['cycles']
                    if next_epoch_data and next_epoch_data['cycles'] else None
                )

                next_epoch_energy = (
                    next_epoch_system_data['power/energy-psys/']
                    if next_epoch_system_data and next_epoch_system_data['power/energy-psys/'] else None
                )


                if next_epoch_ipc is None and next_epoch_energy:
                    print(f'Next epoch IPC is None for {aoicore} in epoch {i+1}. Skipping...')
                else:
                    # Proceed with data aggregation and row construction as before
                    row = {
                        'Experiment_ID': path_date_time,
                        'AOI_Application': aoidata['app'],
                        'AOI_Core': aoicore,
                        'AOI_Cluster': aoi_cluster,
                        'AOI_IPC': next_epoch_ipc,
                        'AOI_Instructions': aoidata.get('instructions', 0),
                        'AOI_LLC_Loads': aoidata.get('LLC-loads', 0),
                        'AOI_LLC_Misses': aoidata.get('LLC-load-misses', 0),
                        'AOI_Stores': aoidata.get('LLC-stores', 0),
                        'AOI_Store_Misses': aoidata.get('LLC-store-misses', 0),
                        'AOI_Cycles': aoidata.get('cycles', 0),
                        'AOI_Branch_Misses': aoidata.get('branch-misses', 0),
                        'AOI_Branches': aoidata.get('branches', 0),
                        'Frequency': aoidata.get('frequency', 0),
                        'Energy': next_epoch_energy,
                        
                    }

                    # Add same cluster characteristics
                    row.update({
                        'Same_Cluster_Applications': ', '.join([data['app'] for data in same_cluster_apps.values()]),
                        'Same_Cluster_Instructions': sum(data.get('instructions', 0) for data in same_cluster_apps.values()),
                        'Same_Cluster_LLC_Loads': sum(data.get('LLC-loads', 0) for data in same_cluster_apps.values()),
                        'Same_Cluster_LLC_Misses': sum(data.get('LLC-load-misses', 0) for data in same_cluster_apps.values()),
                        'Same_Cluster_Stores': sum(data.get('LLC-stores', 0) for data in same_cluster_apps.values()),
                        'Same_Cluster_Store_Misses': sum(data.get('LLC-store-misses', 0) for data in same_cluster_apps.values()),
                        'Same_Cluster_Cycles': sum(data.get('cycles', 0) for data in same_cluster_apps.values()),
                        'Same_Cluster_Branch_Misses': sum(data.get('branch-misses', 0) for data in same_cluster_apps.values()),
                        'Same_Cluster_Branches': sum(data.get('branches', 0) for data in same_cluster_apps.values())
                    })

                    # Add characteristics for Other1 and Other2 clusters
                    row.update({
                        'Other1_Applications': ', '.join([data['app'] for data in other1_apps.values()]),
                        'Other1_Cluster': other1_cluster,
                        'Other1_Instructions': sum(data.get('instructions', 0) for data in other1_apps.values()),
                        'Other1_LLC_Loads': sum(data.get('LLC-loads', 0) for data in other1_apps.values()),
                        'Other1_LLC_Misses': sum(data.get('LLC-load-misses', 0) for data in other1_apps.values()),
                        'Other1_Stores': sum(data.get('LLC-stores', 0) for data in other1_apps.values()),
                        'Other1_Store_Misses': sum(data.get('LLC-store-misses', 0) for data in other1_apps.values()),
                        'Other1_Cycles': sum(data.get('cycles', 0) for data in other1_apps.values()),
                        'Other1_Branch_Misses': sum(data.get('branch-misses', 0) for data in other1_apps.values()),
                        'Other1_Branches': sum(data.get('branches', 0) for data in other1_apps.values())
                    })

                    row.update({
                        'Other2_Applications': ', '.join([data['app'] for data in other2_apps.values()]),
                        'Other2_Cluster': other2_cluster,
                        'Other2_Instructions': sum(data.get('instructions', 0) for data in other2_apps.values()),
                        'Other2_LLC_Loads': sum(data.get('LLC-loads', 0) for data in other2_apps.values()),
                        'Other2_LLC_Misses': sum(data.get('LLC-load-misses', 0) for data in other2_apps.values()),
                        'Other2_Stores': sum(data.get('LLC-stores', 0) for data in other2_apps.values()),
                        'Other2_Store_Misses': sum(data.get('LLC-store-misses', 0) for data in other2_apps.values()),
                        'Other2_Cycles': sum(data.get('cycles', 0) for data in other2_apps.values()),
                        'Other2_Branch_Misses': sum(data.get('branch-misses', 0) for data in other2_apps.values()),
                        'Other2_Branches': sum(data.get('branches', 0) for data in other2_apps.values())
                    })

                    data_rows.append(row)

    return pd.DataFrame(data_rows)

# Main function to process all log files and compile dataset
def process_experiment_results(results_folder):
    dataset = []
    path = results_folder
    for experiment_folder in os.listdir(path):
        #if "2024-11-02_22-37-10_tr_exp_splash2x.radix_bg_spstblcaspspspspspsp_e_core_175" in experiment_folder:
        log_path = os.path.join(path, experiment_folder, 'periodic_counters.log')
        if os.path.isfile(log_path):
            epochs = parse_log_file(log_path)
            dataset.extend(create_dataset(epochs, "", log_path).to_dict(orient='records'))
    return pd.DataFrame(dataset)

# Example usage:
results_df = process_experiment_results(TRAINING_RESULTS_FOLDER+"/dynamic_map_dynamic_freq")
results_df.to_csv('future_contention_energy.csv', index=False)
