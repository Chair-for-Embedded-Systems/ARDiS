import os
import re
import numpy as np
import pandas as pd
import glob
import sys
import json

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import ardis.config as config
import re

def parse_log_file_and_energy(log_file):
    time_points = []
    cumulative_instructions = []
    llc_loads = []
    llc_load_misses = []
    llc_stores = []
    llc_store_misses = []
    cycles = []
    branches = []
    branch_misses = []
    cumulative_energy = []

    with open(log_file, 'r') as file:
        cumulative_instr = 0
        cumulative_llc_load = 0
        cumulative_llc_load_miss = 0
        cumulative_llc_store = 0
        cumulative_llc_store_miss = 0
        cumulative_cycle = 0
        cumulative_branch_miss = 0
        cumulative_branch = 0
        cum_energy = 0
        energy_regex = fr'power/energy-psys/ = (\d+)'

        for line in file:
            # Match the PID lines (performance counters)
            pid_match = re.search(
                r'\[(\d+\.\d+)s\] PID \d+: instructions = (\d+).*LLC-loads = (\d+).*LLC-load-misses = (\d+).*LLC-stores = (\d+).*LLC-store-misses = (\d+).*cycles = (\d+).*branch-misses = (\d+).*branches = (\d+)',
                line)

            # Match the energy values
            energy_match = re.search(fr'\[(\d+\.\d+)s\].*{energy_regex}', line)

            if pid_match:
                time = float(pid_match.group(1))
                instructions = int(pid_match.group(2))
                llc_load = int(pid_match.group(3))
                llc_load_miss = int(pid_match.group(4))
                llc_store = int(pid_match.group(5))
                llc_store_miss = int(pid_match.group(6))
                cycle = int(pid_match.group(7))
                branch_miss = int(pid_match.group(8))
                branch = int(pid_match.group(9))

                # Sanity checks: ensure all values are non-negative
                if any(x < 0 for x in [instructions, llc_load, llc_load_miss, llc_store, llc_store_miss, cycle, branch_miss, branch]):
                    print(f"Warning: Negative value in log at time {time}. Skipping line.")
                    continue

                cumulative_instr += instructions
                cumulative_llc_load += llc_load
                cumulative_llc_load_miss += llc_load_miss
                cumulative_llc_store += llc_store
                cumulative_llc_store_miss += llc_store_miss
                cumulative_cycle += cycle
                cumulative_branch_miss += branch_miss
                cumulative_branch += branch

                time_points.append(time)
                cumulative_instructions.append(cumulative_instr)
                llc_loads.append(cumulative_llc_load)
                llc_load_misses.append(cumulative_llc_load_miss)
                llc_stores.append(cumulative_llc_store)
                llc_store_misses.append(cumulative_llc_store_miss)
                cycles.append(cumulative_cycle)
                branches.append(cumulative_branch)
                branch_misses.append(cumulative_branch_miss)

            if energy_match:
                time = float(energy_match.group(1))
                energy = float(energy_match.group(2))

                # Sanity check: ensure energy is non-negative
                if energy < 0:
                    print(f"Warning: Negative energy value found at time {time}. Skipping line.")
                    continue

                cum_energy += energy
                cumulative_energy.append(cum_energy)

    # Ensure energy and performance data are aligned in time
    if len(cumulative_energy) != len(time_points):
        print(f"Warning: Mismatched lengths between energy and performance data in {log_file}. Adjusting...")
        min_len = min(len(time_points), len(cumulative_energy))
        time_points = time_points[:min_len]
        cumulative_instructions = cumulative_instructions[:min_len]
        llc_loads = llc_loads[:min_len]
        llc_load_misses = llc_load_misses[:min_len]
        llc_stores = llc_stores[:min_len]
        llc_store_misses = llc_store_misses[:min_len]
        cycles = cycles[:min_len]
        branches = branches[:min_len]
        branch_misses = branch_misses[:min_len]
        cumulative_energy = cumulative_energy[:min_len]

    return (time_points, cumulative_instructions, llc_loads, llc_load_misses, llc_stores, llc_store_misses, cycles, branches, branch_misses, cumulative_energy)


# Function to generate the dataset for training with time-based slicing
def generate_training_dataset_time_based(application_name, pcore_files, ecore_files, time_slice, energy_type, frequencies, metric="IPJ"):
    dataset = []

    max_time = max([parse_log_file_and_energy(pf)[0][-1] for pf in pcore_files])  # Find the max time in the logs

    current_time = 0

    while current_time <= max_time:
        next_time = current_time + time_slice
        
        for core_type, core_files in zip(["P-core", "E-core"], [pcore_files, ecore_files]):
            for freq, log_file in zip(frequencies, core_files):
                if not os.path.exists(log_file):
                    print(f"Log file not found for {core_type} at {freq} MHz: {log_file}")
                    continue

                # Parse log files for instructions, energy, and other metrics
                (core_time, core_instr, llc_loads, llc_load_misses, llc_stores, llc_store_misses, cycles, branches, branch_misses, core_energy) = parse_log_file_and_energy(log_file)

                # Ensure that core_instr and core_energy have the same length
                if len(core_instr) != len(core_energy):
                    print(f"Warning: {len(core_instr)} vs {len(core_energy)} Mismatched lengths for instructions and energy in {log_file}. Skipping this log.")
                    continue  # Skip this log file if lengths don't match

                # Interpolate to find the instruction range for the current time slice
                start_instr = np.interp(current_time, core_time, core_instr)
                end_instr = np.interp(next_time, core_time, core_instr)

                # Sanity check for instructions
                if start_instr >= end_instr:
                    print(f"Warning: Start instruction ({start_instr}) >= End instruction ({end_instr}) for {log_file}. Skipping this slice.")
                    continue

                # Find the execution time for this slice
                execution_time = next_time - current_time

                # Find the energy consumption for this slice
                start_energy = np.interp(start_instr, core_instr, core_energy)
                end_energy = np.interp(end_instr, core_instr, core_energy)
                energy_consumed = end_energy - start_energy

                # Interpolate and calculate other metrics (e.g., LLC loads, misses, cycles)
                start_llc_loads = np.interp(start_instr, core_instr, llc_loads)
                end_llc_loads = np.interp(end_instr, core_instr, llc_loads)
                llc_loads_slice = end_llc_loads - start_llc_loads

                start_llc_load_misses = np.interp(start_instr, core_instr, llc_load_misses)
                end_llc_load_misses = np.interp(end_instr, core_instr, llc_load_misses)
                llc_load_misses_slice = end_llc_load_misses - start_llc_load_misses

                start_llc_stores = np.interp(start_instr, core_instr, llc_stores)
                end_llc_stores = np.interp(end_instr, core_instr, llc_stores)
                llc_stores_slice = end_llc_stores - start_llc_stores

                start_llc_store_misses = np.interp(start_instr, core_instr, llc_store_misses)
                end_llc_store_misses = np.interp(end_instr, core_instr, llc_store_misses)
                llc_store_misses_slice = end_llc_store_misses - start_llc_store_misses

                start_cycles = np.interp(start_instr, core_instr, cycles)
                end_cycles = np.interp(end_instr, core_instr, cycles)
                cycles_slice = end_cycles - start_cycles

                start_branches = np.interp(start_instr, core_instr, branches)
                end_branches = np.interp(end_instr, core_instr, branches)
                branches_slice = end_branches - start_branches

                start_branch_misses = np.interp(start_instr, core_instr, branch_misses)
                end_branch_misses = np.interp(end_instr, core_instr, branch_misses)
                branch_misses_slice = end_branch_misses - start_branch_misses

                # Collect all relevant metrics
                dataset.append({
                    "application": application_name,
                    "start_time": current_time,
                    "end_time": next_time,
                    "execution_time": execution_time,
                    "core_type": core_type,
                    "frequency": freq,
                    "start_instruction": start_instr,
                    "end_instruction": end_instr,
                    "instructions": end_instr - start_instr,
                    "energy_psys": energy_consumed,
                    "llc_loads": llc_loads_slice,
                    "llc_load_misses": llc_load_misses_slice,
                    "llc_stores": llc_stores_slice,
                    "llc_store_misses": llc_store_misses_slice,
                    "cycles": cycles_slice,
                    "branches": branches_slice,
                    "branch_misses": branch_misses_slice
                })
                #print(f"Application: {application_name}\tStart Time: {current_time}\tEnd Time: {next_time}\tExecution Time: {execution_time}\tCore Type: {core_type}\tFrequency: {freq}\tStart Instruction: {start_instr}\tEnd Instruction: {end_instr}\tInstructions: {end_instr - start_instr}\tEnergy (psys): {energy_consumed}\tLLC Loads: {llc_loads_slice}\tLLC Load Misses: {llc_load_misses_slice}\tLLC Stores: {llc_stores_slice}\tLLC Store Misses: {llc_store_misses_slice}\tCycles: {cycles_slice}\tBranches: {branches_slice}\tBranch Misses: {branch_misses_slice}")

        current_time = next_time

    df = pd.DataFrame(dataset)

    # Finding the optimal configuration for each time slice
    df = find_optimal_configuration(df, metric)
    
    return df

# Function to find the optimal configuration based on the desired metric
def find_optimal_configuration(df, metric="IPJ"):
    df["optimal_core_type"] = None
    df["optimal_frequency"] = None

    for start_time in df["start_time"].unique():
        slice_data = df[df["start_time"] == start_time]
        print(f"Finding optimal configuration for time slice {start_time}...")
        if metric == "IPJ":
            slice_data["ipj"] = slice_data["instructions"] / slice_data["energy_psys"]

            # Sanity check: ensure IPJ is not NaN or negative
            if np.isnan(slice_data["ipj"].max()):
                print(f"Warning: Invalid IPJ value for time slice {start_time}. Skipping.")
                continue

            best_row = slice_data.loc[slice_data["ipj"].idxmax()]
        elif metric == "EDP":
            slice_data["edp"] = slice_data["energy_psys"] * slice_data["execution_time"]
            best_row = slice_data.loc[slice_data["edp"].idxmin()]

        df.loc[df["start_time"] == start_time, "optimal_core_type"] = best_row["core_type"]
        df.loc[df["start_time"] == start_time, "optimal_frequency"] = best_row["frequency"]
        df.loc[df["start_time"] == start_time, "optimal_efficiency"] = best_row["ipj"]

    return df

# Main function to loop over all applications and generate a single dataset for all applications
def main():
    metric = "IPJ"  # Metric to optimize (IPJ or EDP)
    log_directory = config.PARSEC_FIXED_FREQ_FOLDER

    frequencies = [
        3500,
        3400,
        3300,
        3200,
        3100,
        3000,
        2900,
        2800,
        2700,
        2600,
        2500,
        2400,
        2300,
        2200,
        2100,
        2000,
        1900,
        1800,
        1700,
        1600,
        1500
    ]
    output_directory = os.path.join(config.ROOTPATH, f"{log_directory}/schedules")
    os.makedirs(output_directory, exist_ok=True)

    all_data = []  # Store data for all applications in one list

    # Loop through all applications specified in your config
    for application_name in config.parsec_apps:
        print(f"\nProcessing {application_name}...")

        # Gather log files for P-core and E-core at all frequencies using glob
        pcore_files = [glob.glob(os.path.join(log_directory, f"*_{application_name}_{freq}MHz_Pcore/periodic_counters.log")) for freq in frequencies]
        ecore_files = [glob.glob(os.path.join(log_directory, f"*_{application_name}_{freq}MHz_Ecore/periodic_counters.log")) for freq in frequencies]

        # Flatten the lists to avoid nesting of lists returned by glob
        pcore_files = [item for sublist in pcore_files for item in sublist]
        ecore_files = [item for sublist in ecore_files for item in sublist]

        if not pcore_files or not ecore_files:
            print(f"Skipping {application_name}: Missing log files.")
            continue

        # Time slice size in seconds (e.g., 0.5 seconds = 500 ms)
        time_slice = 0.5

        # Energy type (e.g., "psys")
        energy_type = "psys"

        # Generate the training dataset
        df = generate_training_dataset_time_based(application_name, pcore_files, ecore_files, time_slice, energy_type, frequencies, metric)

        # Append the dataset to the full dataset for all applications
        all_data.append(df)

    # Concatenate all application datasets into one DataFrame
    full_df = pd.concat(all_data)

    # Save the complete dataset
    output_file = os.path.join(output_directory, f"dataset_time_{str(time_slice)}.csv")
    full_df.to_csv(output_file, index=False)
    print(f"Complete dataset saved to {output_file}")


if __name__ == "__main__":
    main()