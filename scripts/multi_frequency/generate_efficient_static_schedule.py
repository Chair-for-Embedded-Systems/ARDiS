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

# Function to parse log file and accumulate instructions
def parse_log_file(log_file):
    time_points = []
    cumulative_instructions = []

    with open(log_file, 'r') as file:
        cumulative_instr = 0
        for line in file:
            match = re.search(r'\[(\d+\.\d+)s\].*instructions = (\d+)', line)
            if match:
                time = float(match.group(1))
                instructions = int(match.group(2))
                cumulative_instr += instructions
                time_points.append(time)
                cumulative_instructions.append(cumulative_instr)
    
    return time_points, cumulative_instructions

# Function to extract and accumulate energy values from log files
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


# Function to find the corresponding time for a specific instruction using interpolation
def find_time_for_instruction(instruction_target, cumulative_instructions, time_points):
    # Check if the instruction target exists directly in the logs
    if instruction_target in cumulative_instructions:
        idx = cumulative_instructions.index(instruction_target)
        return time_points[idx]
    
    # Otherwise, perform linear interpolation to find the time
    for i in range(1, len(cumulative_instructions)):
        if cumulative_instructions[i-1] <= instruction_target <= cumulative_instructions[i]:
            # Linear interpolation between two points
            time_start = time_points[i-1]
            time_end = time_points[i]
            instr_start = cumulative_instructions[i-1]
            instr_end = cumulative_instructions[i]

            # Interpolate to find the corresponding time
            time_for_instruction = time_start + (instruction_target - instr_start) * (time_end - time_start) / (instr_end - instr_start)
            return time_for_instruction
    
    # If the target instruction is outside the range, return the last time
    return time_points[-1]


def generate_static_schedule_with_dvfs(application_name, pcore_files, ecore_files, instruction_slice, energy_type, frequencies, metric="IPJ"):
    # Initialize the static schedule
    static_schedule = []
    
    # Process slices
    current_instr = 0
    phase = 0
    total_phases = 0

    # Determine the total number of slices (phases) for the application
    max_instr = max([parse_log_file(pf)[-1][-1] for pf in pcore_files])  # Assuming all core logs have the same final instruction count
    total_phases = int(np.ceil(max_instr / instruction_slice))

    while current_instr < max_instr:
        next_instr = current_instr + instruction_slice
        print(f"\nSlice {phase + 1} from instruction {current_instr} to {next_instr}:")

        best_metric_value = float('inf') if (metric == "EDP" or metric == "PERF") else 0  # Initialize for comparison
        best_core = None
        best_freq = None
        best_time = None
        best_energy = None

        slice_exists = True  # Flag to check if the slice exists across all core types and frequencies

        # Iterate through core types (P-core and E-core)
        for core_type, core_files in zip(["P-core", "E-core"], [pcore_files, ecore_files]):
            # Iterate through frequencies
            for freq, log_file in zip(frequencies, core_files):
                if not os.path.exists(log_file):
                    print(f"Log file not found for {core_type} at {freq} MHz: {log_file}")
                    slice_exists = False  # Mark slice as missing
                    break  # Break out of the frequency loop for this core type

                # Parse log files for instructions and energy
                core_time, core_instr = parse_log_file(log_file)
                core_energy_time, core_energy = extract_cumulative_energy(log_file, energy_type)

                # Check if the required instructions range is covered in the logs
                if current_instr > core_instr[-1] or next_instr > core_instr[-1]:
                    print(f"\tRequired slice from {current_instr} to {next_instr} not available in {core_type} at {freq} MHz")
                    slice_exists = False
                    break

            if not slice_exists:
                break  # Break out of the core type loop if the slice is missing for any frequency/core

        # Skip the slice if it's not available in all cores and frequencies
        if not slice_exists:
            print(f"\tSkipping slice {phase + 1} due to missing data across core types or frequencies.")
            current_instr = next_instr  # Update for the next slice
            phase += 1
            continue  # Skip to the next slice

        # If the slice exists across all cores and frequencies, find the best configuration
        for core_type, core_files in zip(["P-core", "E-core"], [pcore_files, ecore_files]):
            for freq, log_file in zip(frequencies, core_files):
                core_time, core_instr = parse_log_file(log_file)
                core_energy_time, core_energy = extract_cumulative_energy(log_file, energy_type)

                # Find the execution time for this slice using instruction lookup
                start_time = find_time_for_instruction(current_instr, core_instr, core_time)
                end_time = find_time_for_instruction(next_instr, core_instr, core_time)
                execution_time = end_time - start_time

                # Skip slices that take less than a second
                if execution_time < 0.1:
                    print(f"\tSkipping slice {phase + 1} (execution time = {execution_time:.2f}s < 1s)")
                    continue  # Move to the next configuration
                
                # Find the energy consumption for this slice
                start_energy = np.interp(current_instr, core_instr, core_energy)
                end_energy = np.interp(next_instr, core_instr, core_energy)
                energy_consumed = end_energy - start_energy

                # Calculate the desired metric based on user choice
                instructions_executed = next_instr - current_instr
                if metric == "IPJ":
                    # IPJ = Instructions per Joule
                    energy_efficiency = (instructions_executed / energy_consumed) / 1e6 if energy_consumed > 0 else 0
                    metric_value = energy_efficiency
                elif metric == "EDP":
                    # EDP = Energy * Time (in Joules-seconds)
                    metric_value = energy_consumed * execution_time
                elif metric == "PERF":
                    # PERF = Performance (execution time)
                    metric_value = execution_time

                # Update best configuration if this is better
                if (metric == "IPJ" and metric_value > best_metric_value) or (metric in ["EDP", "PERF"] and metric_value < best_metric_value):
                    best_metric_value = metric_value
                    best_core = core_type
                    best_freq = freq
                    best_time = execution_time
                    best_energy = energy_consumed

        # Skip the first and last slice, and record the best configuration for this slice
        if 0 < phase < total_phases - 1 and best_core is not None and best_freq is not None and best_time is not None and best_energy is not None:
            print(f"Best configuration for slice {phase + 1}: Core = {best_core}, Frequency = {best_freq} MHz, "
                  f"Time = {best_time:.2f}s, Energy = {best_energy:.2f}J, Metric Value = {best_metric_value:.4f}")
            
            # Append the static schedule entry
            static_schedule.append({
                "phase": phase,
                "core": best_core,
                "frequency": best_freq,
                "trigger_instruction": current_instr,
            })

        # Update for the next slice
        current_instr = next_instr
        phase += 1

    return {application_name: static_schedule}


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
    ]  # Available frequencies

    output_directory = os.path.join(config.PARSEC_MIXED_STATIC_FOLDERS, f"{log_directory}/schedules")
    os.makedirs(output_directory, exist_ok=True)



    for instruction_slice in [
        #1e10,
        #5e9,
        #2e9,
        #1e9,
        5e8,
        2e8
        ]:
        all_schedules = {}

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

            # Instruction slice size
            # Energy type (e.g., "psys")
            energy_type = "psys"

            # Generate the static schedule with DVFS
            static_schedule = generate_static_schedule_with_dvfs(application_name, pcore_files, ecore_files, instruction_slice, energy_type, frequencies, metric)

            # Update all schedules with the current application schedule
            all_schedules.update(static_schedule)

        # Save the static schedules for all applications to a JSON file
        with open(os.path.join(output_directory, f"static_schedules_{instruction_slice:.2e}_{metric}.json"), "w") as outfile:
            json.dump(all_schedules, outfile, indent=4)

if __name__ == "__main__":
    main()
