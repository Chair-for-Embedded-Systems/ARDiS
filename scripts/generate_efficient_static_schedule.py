import os
import re
import numpy as np
import pandas as pd
import glob
import sys
import json

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
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

# Function to generate the static schedule based on energy efficiency
def generate_static_schedule(application_name, pcore_file, ecore_file, instruction_slice, energy_type):
    # Parse the logs for instructions and energy
    pcore_time, pcore_instr = parse_log_file(pcore_file)
    ecore_time, ecore_instr = parse_log_file(ecore_file)
    pcore_energy_time, pcore_energy = extract_cumulative_energy(pcore_file, energy_type)
    ecore_energy_time, ecore_energy = extract_cumulative_energy(ecore_file, energy_type)

    # Initialize the static schedule
    static_schedule = []
    
    # Process the E-core first
    ecore_index = 0
    pcore_index = 0
    current_instr = 0
    phase = 0
    
    while current_instr < ecore_instr[-1]:
        next_instr = current_instr + instruction_slice

        # Find the time and energy on the E-core where this slice ends
        while ecore_index < len(ecore_instr) and ecore_instr[ecore_index] < next_instr:
            ecore_index += 1
        ecore_end_energy = ecore_energy[ecore_index] if ecore_index < len(ecore_energy) else ecore_energy[-1]

        # Find corresponding time and energy on P-core
        while pcore_index < len(pcore_instr) and pcore_instr[pcore_index] < next_instr:
            pcore_index += 1
        pcore_end_energy = pcore_energy[pcore_index] if pcore_index < len(pcore_energy) else pcore_energy[-1]

        # Calculate energy consumed during the phase
        ecore_energy_consumed = ecore_end_energy - (ecore_energy[ecore_index-1] if ecore_index > 0 else 0)
        pcore_energy_consumed = pcore_end_energy - (pcore_energy[pcore_index-1] if pcore_index > 0 else 0)

        # Calculate energy efficiency in MInstr/J
        ecore_instructions_executed = next_instr - current_instr
        pcore_instructions_executed = next_instr - current_instr

        ecore_efficiency = (ecore_instructions_executed / ecore_energy_consumed) / 1e6 if ecore_energy_consumed > 0 else 0
        pcore_efficiency = (pcore_instructions_executed / pcore_energy_consumed) / 1e6 if pcore_energy_consumed > 0 else 0

        # Determine which core is more efficient for this phase
        selected_core = 6 if ecore_efficiency > pcore_efficiency else 16

        # Append the static schedule entry
        static_schedule.append({
            "phase": phase,
            "core": selected_core,
            "trigger_instruction": current_instr,
        })

        # Update for the next slice
        current_instr = next_instr
        phase += 1

    return {application_name: static_schedule}

# Main script to process all applications and generate static schedules
def main():
    log_directory = config.RESULTS_FOLDER
    frequency = "2500MHz"
    
    output_directory = os.path.join(config.ROOTPATH, f"{log_directory}/schedules/{frequency}")
    os.makedirs(output_directory, exist_ok=True)

    all_schedules = {}

    for application_name in config.spec_apps:
        pcore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Pcore"))
        ecore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Ecore"))

        if not (pcore_dirs and ecore_dirs):
            print(f"Skipping {application_name}: Missing log files.")
            continue

        pcore_file = os.path.join(pcore_dirs[0], "periodic_counters.log")
        ecore_file = os.path.join(ecore_dirs[0], "periodic_counters.log")

        if not (os.path.exists(pcore_file) and os.path.exists(ecore_file)):
            print(f"Skipping {application_name}: Missing log files.")
            continue

        instruction_slice = 2e9

        #energy_type = "cores"
        #energy_type = "pkg"
        energy_type = "psys"
        static_schedule = generate_static_schedule(application_name, pcore_file, ecore_file, instruction_slice, energy_type)
        all_schedules.update(static_schedule)

    # Save the static schedules to a JSON file
    with open(os.path.join(output_directory, f"static_schedules_{energy_type}_{instruction_slice/1e9}.json"), "w") as outfile:
        json.dump(all_schedules, outfile, indent=4)

if __name__ == "__main__":
    main()
