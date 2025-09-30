"""
    This script generates a plot that shows the cumulative instructions and instantaneous instructions over time for a specific application.
    A specific slice is highlighted in red, and the energy consumed during that slice is calculated and displayed along with the IPJ.
"""

import os
import re
import numpy as np
import glob
import sys
import matplotlib.pyplot as plt

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
import ardis.config as config

# Enable LaTeX rendering in Matplotlib (if needed)
# plt.rcParams.update({...})

# Function to parse log file and extract instructions
def parse_log_file(log_file):
    exec_time_points = []
    energy_time_points = []
    instantaneous_instructions = []
    instantaneous_energy = []

    with open(log_file, 'r') as file:
        energy_regex = fr'power/energy-psys/ = (\d+)'
        for line in file:
            if "] PID" in line:
                match = re.search(r'\[(\d+\.\d+)s\].*instructions = (\d+)', line)
                if match:
                    time = float(match.group(1))
                    instructions = int(match.group(2))  # Instantaneous instructions from the log
                    exec_time_points.append(time)
                    instantaneous_instructions.append(instructions)
            elif "] SYSTEM:" in line:
                match = re.search(fr'\[(\d+\.\d+)s\].*{energy_regex}', line)
                if match:
                    time = float(match.group(1))
                    energy = float(match.group(2))
                    energy_time_points.append(time)
                    instantaneous_energy.append(energy)
    assert len(exec_time_points) == len(energy_time_points) and len(energy_time_points) == len(instantaneous_instructions) and len(instantaneous_instructions) == len(instantaneous_energy)
    return exec_time_points, instantaneous_instructions, instantaneous_energy

# Function to find the corresponding time for a specific instruction using interpolation
def find_time_for_instruction(instruction_target, cumulative_instructions, time_points):
    # Find the exact match or perform interpolation if needed
    idx = np.where(cumulative_instructions == instruction_target)[0]
    
    if len(idx) > 0:
        # If an exact match is found, return the corresponding time
        return time_points[idx[0]]
    
    # If no exact match, perform linear interpolation
    for i in range(1, len(cumulative_instructions)):
        if cumulative_instructions[i-1] <= instruction_target <= cumulative_instructions[i]:
            time_start = time_points[i-1]
            time_end = time_points[i]
            instr_start = cumulative_instructions[i-1]
            instr_end = cumulative_instructions[i]

            # Perform linear interpolation to find the corresponding time
            time_for_instruction = time_start + (instruction_target - instr_start) * (time_end - time_start) / (instr_end - instr_start)
            return time_for_instruction
    
    # If the target instruction is outside the range, return the last time
    return time_points[-1]

def energy_consumed(instructions, energy, start_instr, end_instr):
    # Interpolate the energy values at instruction counts X and Y
    energy_X = np.interp(start_instr, instructions, energy)
    energy_Y = np.interp(end_instr, instructions, energy)
    
    # Calculate the energy consumed between X and Y
    return energy_X, energy_Y


# Function to highlight a randomly selected slice across frequencies and core types
def highlight_slice(start_instr, end_instr, cumulative_instructions, time_points, duration, energy_consumed):
    start_time = find_time_for_instruction(start_instr, cumulative_instructions, time_points)
    end_time = find_time_for_instruction(end_instr, cumulative_instructions, time_points)
    plt.axvspan(start_time, end_time, color='red', label=f"{duration:.2f}s & {energy_consumed:.2f} IPJ", alpha=0.3)

# Function to generate slices and highlight a selected slice
def generate_slices(application_name, core_type, log_files, frequencies, instruction_slice, energy_type, highlight_start, highlight_end):
    slice_data = []
    freq_index = 0

    for freq, log_file in zip(frequencies, log_files):
        if not os.path.exists(log_file):
            print(f"Log file not found for {core_type} at {freq} MHz: {log_file}")
            continue

        time_points, instantaneous_instructions, instantaneous_energy = parse_log_file(log_file)

        cumulative_instructions = np.cumsum(instantaneous_instructions)
        cumulative_energy = np.cumsum(instantaneous_energy)

        #print(cumulative_instructions)
        #print(cumulative_energy)
        
        max_instr = cumulative_instructions[-1]
        current_instr = 0
        slice_num = 1

        ax1 = plt.subplot(2, len(frequencies), freq_index + 1 if core_type == "P-core" else freq_index + 1 + len(frequencies))
        ax1.plot(time_points, cumulative_instructions, label=f"Cumulative", color='blue')

        ax2 = ax1.twinx()
        ax2.plot(time_points, instantaneous_instructions, label=f"Instantaneous", color='black')
        ax2.set_ylabel('Instantaneous Instructions (inst/s)')

        while current_instr < max_instr:
            next_instr = current_instr + instruction_slice

            start_time = find_time_for_instruction(current_instr, cumulative_instructions, time_points)
            end_time = find_time_for_instruction(next_instr, cumulative_instructions, time_points)
            execution_time = end_time - start_time

            print(f"Slice {slice_num}: {current_instr} - {next_instr} ({execution_time:.2f}s)")
            print(f"Start time: {start_time:.2f}s, End time: {end_time:.2f}s")
            start_energy, end_energy = energy_consumed(cumulative_instructions, cumulative_energy, current_instr, next_instr)
            consumed_energy = end_energy - start_energy
            efficiency = ((next_instr - current_instr) / consumed_energy) * 1e-6 if consumed_energy > 0 else 0


            print(f"Start energy:{start_energy:.2f} \t End energy:{end_energy:.2f} \t Consumed energy:{consumed_energy:.2f} \tEfficiency: {efficiency:.2f} IPJ")
            slice_data.append({
                "application": application_name,
                "core_type": core_type,
                "frequency": freq,
                "slice_number": slice_num,
                "starting_instruction": current_instr,
                "ending_instruction": next_instr,
                "starting_time": start_time,
                "ending_time": end_time,
                "duration": execution_time,
                "efficiency": efficiency
            })

            ax1.axvline(x=start_time, color='r', linestyle='--', alpha=0.4)
            ax1.axvline(x=end_time, color='r', linestyle='--', alpha=0.4)

            if current_instr <= highlight_start and next_instr >= highlight_end:
                highlight_slice(highlight_start, highlight_end, cumulative_instructions, time_points, execution_time, efficiency)

            current_instr = next_instr
            slice_num += 1

        ax1.set_title(f"{core_type} - {freq} MHz")
        ax1.set_xlabel("Time (s)")
        ax1.set_ylabel("Cumulative Instructions")
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')

        freq_index += 1

    return slice_data

def main():
    log_directory = config.PARSEC_FIXED_FREQ_FOLDER
    frequencies = [1500, 2000, 2500, 3000, 3500]
    application_name = "parsec-dedup"
    print(f"\nProcessing {application_name}...")

    pcore_files = [glob.glob(os.path.join(log_directory, f"*_{application_name}_{freq}MHz_Pcore/periodic_counters.log")) for freq in frequencies]
    ecore_files = [glob.glob(os.path.join(log_directory, f"*_{application_name}_{freq}MHz_Ecore/periodic_counters.log")) for freq in frequencies]

    pcore_files = [item for sublist in pcore_files for item in sublist]
    ecore_files = [item for sublist in ecore_files for item in sublist]

    if not pcore_files or not ecore_files:
        print(f"Skipping {application_name}: Missing log files.")
        return

    instruction_slice = 1e9
    energy_type = "psys"
    random_start = 2e9
    random_end = 3e9

    plt.figure(figsize=(18, 6))

    generate_slices(application_name, "P-core", pcore_files, frequencies, instruction_slice, energy_type, random_start, random_end)
    generate_slices(application_name, "E-core", ecore_files, frequencies, instruction_slice, energy_type, random_start, random_end)

    plt.tight_layout()
    output_image_file = f"{application_name}_highlighted_energy_slicing_plot.png"
    plt.savefig(output_image_file, dpi=300)
    print(f"Figure saved as {output_image_file}")


if __name__ == "__main__":
    main()