import os
import re
import numpy as np
import pandas as pd
import glob
import sys
import json

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

def parse_log_file(log_file):
    time_points = []
    cumulative_instructions = []
    llc_loads = []
    llc_load_misses = []
    llc_stores = []
    llc_store_misses = []
    cycles = []
    branches = []
    branch_misses = []

    with open(log_file, 'r') as file:
        cumulative_instr = 0
        for line in file:
            # Match the PID lines
            pid_match = re.search(
                r'\[(\d+\.\d+)s\] PID \d+: instructions = (\d+).*LLC-loads = (\d+).*LLC-load-misses = (\d+).*LLC-stores = (\d+).*LLC-store-misses = (\d+).*cycles = (\d+).*branch-misses = (\d+).*branches = (\d+)',
                line)
            
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
                #print(f"Time: {time}, Instructions: {instructions}, LLC-loads: {llc_load}, LLC-load-misses: {llc_load_miss}, LLC-stores: {llc_store}, LLC-store-misses: {llc_store_miss}, Cycles: {cycle}, Branch-misses: {branch_miss}, Branches: {branch}")
                cumulative_instr += instructions
                time_points.append(time)
                cumulative_instructions.append(cumulative_instr)
                llc_loads.append(llc_load)
                llc_load_misses.append(llc_load_miss)
                llc_stores.append(llc_store)
                llc_store_misses.append(llc_store_miss)
                cycles.append(cycle)
                branches.append(branch)
                branch_misses.append(branch_miss)
    
    return time_points, cumulative_instructions, llc_loads, llc_load_misses, llc_stores, llc_store_misses, cycles, branches, branch_misses



# Function to extract and accumulate energy values from log files (unchanged)
def extract_cumulative_energy(log_file, energy_type):
    time_points = []
    cumulative_energy = []

    with open(log_file, 'r') as file:
        cum_energy = 0
        energy_regex = fr'power/energy-{energy_type}/ = (\d+)'
        for line in file:
            match = re.search(fr'\[(\d+\.\d+)s\].*{energy_regex}', line)
            if match:
                time = float(match.group(1))
                energy = float(match.group(2))
                cum_energy += energy
                time_points.append(time)
                cumulative_energy.append(cum_energy)
    
    return time_points, cumulative_energy

# Function to find the corresponding time for a specific instruction using interpolation (unchanged)
def find_time_for_instruction(instruction_target, cumulative_instructions, time_points):
    if instruction_target in cumulative_instructions:
        idx = cumulative_instructions.index(instruction_target)
        return time_points[idx]
    
    for i in range(1, len(cumulative_instructions)):
        if cumulative_instructions[i-1] <= instruction_target <= cumulative_instructions[i]:
            time_start = time_points[i-1]
            time_end = time_points[i]
            instr_start = cumulative_instructions[i-1]
            instr_end = cumulative_instructions[i]

            time_for_instruction = time_start + (instruction_target - instr_start) * (time_end - time_start) / (instr_end - instr_start)
            return time_for_instruction
    
    return time_points[-1]

# Generate the dataset for training with more periodic counters included
def generate_training_dataset(application_name, pcore_files, ecore_files, instruction_slice, energy_type, frequencies, metric="IPJ"):
    dataset = []

    current_instr = 0
    max_instr = max([parse_log_file(pf)[1][-1] for pf in pcore_files])

    while current_instr < max_instr:
        next_instr = current_instr + instruction_slice
        for core_type, core_files in zip(["P-core", "E-core"], [pcore_files, ecore_files]):
            for freq, log_file in zip(frequencies, core_files):
                if not os.path.exists(log_file):
                    print(f"Log file not found for {core_type} at {freq} MHz: {log_file}")
                    continue

                # Parse log files for instructions and energy, and extract additional counters
                (core_time, core_instr, llc_loads, llc_load_misses, llc_stores, llc_store_misses, cycles, branches, branch_misses) = parse_log_file(log_file)
                core_energy_time, core_energy = extract_cumulative_energy(log_file, energy_type)

                # Check if the required instructions range is covered in the logs
                if current_instr > core_instr[-1] or next_instr > core_instr[-1]:
                    continue

                # Ensure that core_instr and core_energy have the same length
                if len(core_instr) != len(core_energy):
                    print(f"Warning: Mismatched lengths for instructions and energy in {log_file}. Skipping this log.")
                    continue  # Skip this log file if lengths don't match


                # Find the execution time for this slice using instruction lookup
                print(len(core_instr), len(core_time), len(llc_loads), len(llc_load_misses), len(llc_stores), len(llc_store_misses), len(cycles), len(branches), len(branch_misses))

                start_time = find_time_for_instruction(current_instr, core_instr, core_time)
                end_time = find_time_for_instruction(next_instr, core_instr, core_time)
                execution_time = end_time - start_time

                # Find the energy consumption for this slice
                start_energy = np.interp(current_instr, core_instr, core_energy)
                end_energy = np.interp(next_instr, core_instr, core_energy)
                energy_consumed = end_energy - start_energy

                # Find the values for other metrics using interpolation at two points
                start_llc_loads = np.interp(current_instr, core_instr, llc_loads)
                end_llc_loads = np.interp(next_instr, core_instr, llc_loads)
                llc_loads_slice = end_llc_loads - start_llc_loads

                start_llc_load_misses = np.interp(current_instr, core_instr, llc_load_misses)
                end_llc_load_misses = np.interp(next_instr, core_instr, llc_load_misses)
                llc_load_misses_slice = end_llc_load_misses - start_llc_load_misses

                start_llc_stores = np.interp(current_instr, core_instr, llc_stores)
                end_llc_stores = np.interp(next_instr, core_instr, llc_stores)
                llc_stores_slice = end_llc_stores - start_llc_stores

                start_llc_store_misses = np.interp(current_instr, core_instr, llc_store_misses)
                end_llc_store_misses = np.interp(next_instr, core_instr, llc_store_misses)
                llc_store_misses_slice = end_llc_store_misses - start_llc_store_misses

                start_cycles = np.interp(current_instr, core_instr, cycles)
                end_cycles = np.interp(next_instr, core_instr, cycles)
                cycles_slice = end_cycles - start_cycles

                start_branches = np.interp(current_instr, core_instr, branches)
                end_branches = np.interp(next_instr, core_instr, branches)
                branches_slice = end_branches - start_branches

                start_branch_misses = np.interp(current_instr, core_instr, branch_misses)
                end_branch_misses = np.interp(next_instr, core_instr, branch_misses)
                branch_misses_slice = end_branch_misses - start_branch_misses

                # Collect all relevant metrics
                dataset.append({
                    "application": application_name,
                    "start_instruction": current_instr,
                    "end_instruction": next_instr,
                    "execution_time": execution_time,
                    "core_type": core_type,
                    "frequency": freq,
                    "instructions": next_instr - current_instr,
                    "energy_psys": energy_consumed,
                    "llc_loads": llc_loads_slice,
                    "llc_load_misses": llc_load_misses_slice,
                    "llc_stores": llc_stores_slice,
                    "llc_store_misses": llc_store_misses_slice,
                    "cycles": cycles_slice,
                    "branches": branches_slice,
                    "branch_misses": branch_misses_slice
                })

        current_instr = next_instr

    df = pd.DataFrame(dataset)

    # Finding the optimal configuration for each slice
    df = find_optimal_configuration(df, metric)
    
    return df

# Function to find the optimal configuration based on the desired metric
def find_optimal_configuration(df, metric="IPJ"):
    df["optimal_core_type"] = None
    df["optimal_frequency"] = None

    for start_instr in df["start_instruction"].unique():
        slice_data = df[df["start_instruction"] == start_instr]

        if metric == "IPJ":
            slice_data["ipj"] = slice_data["instructions"] / slice_data["energy_psys"]
            best_row = slice_data.loc[slice_data["ipj"].idxmax()]
        elif metric == "EDP":
            slice_data["edp"] = slice_data["energy_psys"] * slice_data["execution_time"]
            best_row = slice_data.loc[slice_data["edp"].idxmin()]

        df.loc[df["start_instruction"] == start_instr, "optimal_core_type"] = best_row["core_type"]
        df.loc[df["start_instruction"] == start_instr, "optimal_frequency"] = best_row["frequency"]
        df.loc[df["start_instruction"] == start_instr, "optimal_efficiency"] = best_row["ipj"]

    return df

# Main function to loop over all applications and generate a single dataset for all applications
def main():
    metric = "IPJ"  # Metric to optimize (IPJ or EDP)
    log_directory = config.PARSEC_FIXED_FREQ_FOLDER
    frequencies = [
        1500,
        2000,
        2500,
        3000,
        3500
    ]  # Available frequencies

    output_directory = os.path.join(config.ROOTPATH, f"{log_directory}/schedules")
    os.makedirs(output_directory, exist_ok=True)

    all_data = []  # Store data for all applications in one list

    # Loop through all applications specified in your config
    for application_name in config.parsec_apps:
        #application_name = "parsec-dedup"
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

        # Instruction slice size
        instruction_slice = 1e9

        # Energy type (e.g., "psys")
        energy_type = "psys"

        # Generate the training dataset
        df = generate_training_dataset(application_name, pcore_files, ecore_files, instruction_slice, energy_type, frequencies, metric)

        # Append the dataset to the full dataset for all applications
        all_data.append(df)

    # Concatenate all application datasets into one DataFrame
    full_df = pd.concat(all_data)

    # Save the complete dataset
    output_file = os.path.join(output_directory, f"all_applications_training_dataset_{str(instruction_slice)}.csv")
    full_df.to_csv(output_file, index=False)
    print(f"Complete dataset saved to {output_file}")


if __name__ == "__main__":
    main()
