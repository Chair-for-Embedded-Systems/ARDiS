"""
    This is the script used to generate the figures for the energy efficiency phases of the applications in the paper.
"""

import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import glob
import sys

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import ardis.config as config

# Enable LaTeX rendering in Matplotlib (if needed)
plt.rcParams.update({
    "text.usetex": True,  # Use LaTeX to render text
    "font.family": "serif",  # Use serif fonts
    "font.serif": ["Times"],  # Use Times font for the plot
    "axes.labelsize": 20,  # Font size for axis labels
    "axes.labelweight": "bold",  # Make axis labels bold
    "xtick.labelsize": 18,  # Font size for x-axis tick labels
    "ytick.labelsize": 18,  # Font size for y-axis tick labels
    "legend.fontsize": 18,  # Font size for the legend
    "axes.titlesize": 20  # Font size for the title
})

# Function to parse log file and accumulate instructions
def parse_log_file(log_file):
    time_points = []
    cumulative_instructions = []
    periodic_instructions = []

    with open(log_file, 'r') as file:
        cumulative_instr = 0
        for line in file:
            if "PID" in line:
                match = re.search(r'\[(\d+\.\d+)s\].*instructions = (\d+)', line)
                if match:
                    time = float(match.group(1))
                    instructions = int(match.group(2))
                    cumulative_instr += instructions
                    time_points.append(time)
                    cumulative_instructions.append(cumulative_instr)
                    periodic_instructions.append(instructions)
    
    return time_points, cumulative_instructions, periodic_instructions

# Function to extract and accumulate energy values from log files
def extract_cumulative_energy(log_file, energy_type):
    time_points = []
    cumulative_energy = []
    periodic_energy = []

    with open(log_file, 'r') as file:
        cum_energy = 0
        energy_regex = fr'power/energy-{energy_type}/ = (\d+\.\d+)'
        for line in file:
            if "SYSTEM" in line:
                match = re.search(fr'\[(\d+\.\d+)s\].*{energy_regex}', line)
                if match:
                    time = float(match.group(1))
                    energy = float(match.group(2))
                    cum_energy += energy
                    time_points.append(time)
                    cumulative_energy.append(cum_energy)
                    periodic_energy.append(energy)
    
    return time_points, cumulative_energy, periodic_energy

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
# Updated generate_lookup_table function with boundary checks
def generate_lookup_table(application_name, pcore_file, ecore_file, instruction_slice, energy_type):
    # Parse the logs for instructions and energy
    pcore_time, pcore_instr, _ = parse_log_file(pcore_file)
    ecore_time, ecore_instr, _ = parse_log_file(ecore_file)
    pcore_energy_time, pcore_energy, _ = extract_cumulative_energy(pcore_file, energy_type)
    ecore_energy_time, ecore_energy, _ = extract_cumulative_energy(ecore_file, energy_type)
    assert len(pcore_instr) == len(pcore_energy), "EnerInstructions and energy values do not match for P-core"
    assert len(ecore_instr) == len(ecore_energy), "EnerInstructions and energy values do not match for E-core"

    # Initialize the lookup table
    lookup_table = []

    current_instr = 0
    
    while current_instr < ecore_instr[-1]:
        next_instr = current_instr + instruction_slice

        # Use interpolation to find the start and end times for the E-core and P-core
        ecore_start_time = find_time_for_instruction(current_instr, ecore_instr, ecore_time)
        ecore_end_time = find_time_for_instruction(next_instr, ecore_instr, ecore_time)
        pcore_start_time = find_time_for_instruction(current_instr, pcore_instr, pcore_time)
        pcore_end_time = find_time_for_instruction(next_instr, pcore_instr, pcore_time)

        # Calculate the duration of the slice on each core
        ecore_duration = ecore_end_time - ecore_start_time
        pcore_duration = pcore_end_time - pcore_start_time

        # Ensure valid range for energy calculations
        ecore_index_start = np.searchsorted(ecore_instr, current_instr)
        ecore_index_end = np.searchsorted(ecore_instr, next_instr)
        pcore_index_start = np.searchsorted(pcore_instr, current_instr)
        pcore_index_end = np.searchsorted(pcore_instr, next_instr)

        # Adjust indices to prevent out-of-range errors
        ecore_index_start = min(max(ecore_index_start, 0), len(ecore_energy) - 1)
        ecore_index_end = min(max(ecore_index_end, 0), len(ecore_energy) - 1)
        pcore_index_start = min(max(pcore_index_start, 0), len(pcore_energy) - 1)
        pcore_index_end = min(max(pcore_index_end, 0), len(pcore_energy) - 1)

        # Calculate energy consumed during the phase
        ecore_start_energy = ecore_energy[ecore_index_start]
        ecore_end_energy = ecore_energy[ecore_index_end]
        pcore_start_energy = pcore_energy[pcore_index_start]
        pcore_end_energy = pcore_energy[pcore_index_end]

        ecore_energy_consumed = ecore_end_energy - ecore_start_energy
        pcore_energy_consumed = pcore_end_energy - pcore_start_energy

        if ecore_energy_consumed <= 0:
            print(f"Debug: E-core zero or negative energy consumption at slice {current_instr} to {next_instr}")
        if pcore_energy_consumed <= 0:
            print(f"Debug: P-core zero or negative energy consumption at slice {current_instr} to {next_instr}")

        # Calculate energy efficiency in MInstr/J
        ecore_instructions_executed = next_instr - current_instr
        pcore_instructions_executed = next_instr - current_instr

        ecore_efficiency = (ecore_instructions_executed / ecore_energy_consumed) / 1e6 if ecore_energy_consumed > 0 else np.nan
        pcore_efficiency = (pcore_instructions_executed / pcore_energy_consumed) / 1e6 if pcore_energy_consumed > 0 else np.nan

        # Calculate the percentage improvement of E-core over P-core
        if pcore_efficiency > 0:
            percentage_improvement = ((ecore_efficiency - pcore_efficiency) / pcore_efficiency) * 100
        else:
            percentage_improvement = np.nan

        # Record the results
        lookup_table.append({
            "Application": application_name,
            "Energy Type": energy_type,
            "Instruction Start": current_instr,
            "Instruction End": next_instr,
            "E-core Start Time (s)": ecore_start_time,
            "E-core End Time (s)": ecore_end_time,
            "E-core Duration (s)": ecore_duration,
            "E-core Energy (J)": ecore_energy_consumed,
            "P-core Start Time (s)": pcore_start_time,
            "P-core End Time (s)": pcore_end_time,
            "P-core Duration (s)": pcore_duration,
            "P-core Energy (J)": pcore_energy_consumed,
            "E-core Efficiency (MInstr/J)": ecore_efficiency,
            "P-core Efficiency (MInstr/J)": pcore_efficiency,
            "E-core Efficiency Improvement (%)": percentage_improvement
        })

        current_instr = next_instr

    return lookup_table



def generate_efficiency_plot(application_name, lookup_table, pcore_file, ecore_file, output_directory, energy_type, instruction_slice, frequency_raw):
    # Parse the logs again for detailed plotting
    
    pcore_time, pcore_instr, pcore_periodic_instr = parse_log_file(pcore_file)
    ecore_time, ecore_instr, ecore_periodic_instr = parse_log_file(ecore_file)

    pcore_energy_time, pcore_energy, pcore_periodic_energy = extract_cumulative_energy(pcore_file, energy_type)
    ecore_energy_time, ecore_energy, ecore_periodic_energy = extract_cumulative_energy(ecore_file, energy_type)

    # Calculate periodic instructions (difference between consecutive instruction counts)
    pcore_periodic_ipj =  np.asarray(pcore_periodic_instr) / np.asarray(pcore_periodic_energy)
    ecore_periodic_ipj =  np.asarray(ecore_periodic_instr) / np.asarray(ecore_periodic_energy)


    # Filter the lookup table for the current energy type
    lookup_table_filtered = [row for row in lookup_table if row['Energy Type'] == energy_type]

    # Handle the case when lookup_table_filtered is empty
    if not lookup_table_filtered:
        print(f"No data available for {application_name} with energy type {energy_type}. Skipping plot generation.")
        return  # Exit the function early

        
        # Create subplots (1x2 layout for E-core and P-core side by side)
    fig, axs = plt.subplots(2, 1, figsize=(10, 6), sharey=True)

    # Colors for the phases
    colors = plt.cm.viridis(np.linspace(0, 1, len(lookup_table_filtered)))

    ### E-core Plot (Left Plot) ###
    # Plot cumulative instructions for E-core
    
    instruction_slice_text = '800-million-Instr. Slice' if instruction_slice == 8e8 else '2-billion-Instr. Slice'
    display_app_name = application_name.replace("parsec-","")



    axs[0].grid(True, which='both', linestyle='-', linewidth=1.2, color='#333', alpha=0.2)
    axs[1].grid(True, which='both', linestyle='-', linewidth=1.2, color='#333', alpha=0.2)
    axs[1].plot(ecore_time, ecore_instr, color="#38369A", label="Cumulative Instructions")
    axs[1].set_xlabel("Time (s)")
    axs[1].set_ylabel("Cumul. Instructions")
    axs[1].set_title(f"{display_app_name} - E core Execution - {frequency_raw/1000:.1f} GHz - {instruction_slice_text}")
    #axs[0].set_title(f"{application_name} - E-core Energy Efficiency and Phases ({energy_type})")

    # Plot periodic instructions for E-core
    ax2 = axs[1].twinx()
    ax2.plot(ecore_time, ecore_periodic_energy, '--', color="#061A40", label="Periodic Energy", alpha=0.3)
    ax2.set_ylabel("Energy (J)")

    # Highlight phases for E-core and add slice number and percentage improvement annotations
    for i, row in enumerate(lookup_table_filtered):
        start_instr = row['Instruction Start']
        end_instr = row['Instruction End']

        start_index = np.searchsorted(ecore_instr, start_instr)
        end_index = np.searchsorted(ecore_instr, end_instr)

        start_index = min(start_index, len(ecore_time) - 1)
        end_index = min(end_index, len(ecore_time) - 1)

        start_time = ecore_time[start_index]
        end_time = ecore_time[end_index]

        #if i == max_improvement_index:
        #    highlight_alpha = 0.5
        #    highlight_color = 'gold'
        #elif i == min_improvement_index:
        #    highlight_alpha = 0.5
        #    highlight_color = 'lightcoral'
        #else:
        highlight_alpha = 0.3
        highlight_color = colors[i]

        axs[1].axvspan(
            start_time, end_time, color=highlight_color, alpha=highlight_alpha, edgecolor=None,
            linewidth=1
        )

        annotation_time = (start_time + end_time) / 2
        annotation_instr = (start_instr + end_instr) / 2
        fixed_position = 0.3e10
        phase_number = f"Phase {i+1}"
        absolute_text = f"{row['E-core Efficiency (MInstr/J)']:.1f}"
        improvement_text = f"{'+' if row['E-core Efficiency Improvement (%)'] > 0 else ''} {row['E-core Efficiency Improvement (%)']:.1f}\%"
        #axs[1].text(
        #    annotation_time, fixed_position, phase_number, color="black", ha="center", va="bottom",
        #    fontsize=16, fontweight='bold', bbox=dict(facecolor='white', edgecolor='#032B43', pad=2), rotation=90
        #)
        #axs[1].text(
        #    annotation_time, fixed_position, absolute_text, color="black", ha="center", va="bottom",
        #    fontsize=16, fontweight='bold', bbox=dict(facecolor='white', edgecolor='#032B43', pad=2), rotation=90
        #)
        improvement_box_color = '#FCC8B2' if row['E-core Efficiency Improvement (%)'] < 0 else '#C6D8AF'
        axs[1].text(
            annotation_time, fixed_position, improvement_text, color='black' if row['E-core Efficiency Improvement (%)'] < 0 else 'black', ha="center", va="bottom",
            fontsize=16, bbox=dict(facecolor=improvement_box_color, edgecolor='none', pad=2), rotation=90
        )

    ### P-core Plot (Right Plot) ###
    axs[0].plot(pcore_time, pcore_instr, color="#38369A", label="Cumulative Instructions")
    #axs[0].set_xlabel("Time (s)")
    axs[0].set_ylabel("Cumul. Instructions")
    axs[0].set_title(f"{display_app_name} - P core Execution - {frequency_raw/1000:.1f} GHz - {instruction_slice_text}")

    ax3 = axs[0].twinx()
    ax3.plot(pcore_time, pcore_periodic_energy, '--', color="#061A40", label="Perioidic Energy", alpha=0.3)
    ax3.set_ylabel("Energy (J)")

    for i, row in enumerate(lookup_table_filtered):
        start_instr = row['Instruction Start']
        end_instr = row['Instruction End']

        start_index = np.searchsorted(pcore_instr, start_instr)
        end_index = np.searchsorted(pcore_instr, end_instr)

        start_index = min(start_index, len(pcore_time) - 1)
        end_index = min(end_index, len(pcore_time) - 1)

        start_time = pcore_time[start_index]
        end_time = pcore_time[end_index]

        highlight_alpha = 0.3
        highlight_color = colors[i]

        axs[0].axvspan(
            start_time, end_time, color=highlight_color, alpha=highlight_alpha, edgecolor=None,
            linewidth=1
        )

        fixed_position = 0.25e10
        annotation_time = (start_time + end_time) / 2
        annotation_instr = (start_instr + end_instr) / 2

        absolute_text = f"Phase {i+1}: {row['P-core Efficiency (MInstr/J)']:.2f}"
        #axs[0].text(
        #    annotation_time, fixed_position, absolute_text, color="black", ha="center", va="bottom",
        #    fontsize=16, bbox=dict(facecolor='white', edgecolor='#032B43', pad=2), rotation=90
        #)

    # Add legends
    axs[0].legend(loc="upper left")
    ax2.legend(loc="upper right")
    axs[1].legend(loc="upper left")
    ax3.legend(loc="upper right")

    # Adjust layout for better spacing
    plt.tight_layout(pad=1.0)
    plt.savefig(os.path.join(output_directory, f"{application_name}_efficiency_phases_{instruction_slice:.1e}.pdf"), dpi=300, format='pdf')
    plt.close()


# Main script to process all applications
def main():
    # Ensure the output directory exists

    log_directory = config.PARSEC_FIXED_FREQ_FOLDER

    frequency = "2500MHz"
    frequency_raw = 2500

    
    output_directory = os.path.join(config.PAPERPLOT_FOLDER, f"energy_efficiency_phases/{frequency}")
    os.makedirs(output_directory, exist_ok=True)

    all_lookup_tables = []

    #for application_name in config.parsec_apps:
    application_name = "parsec-splash2x.radix"
    # Use glob to find the directories matching the application name for P-core and E-core at 2000MHz
    pcore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Pcore"))
    ecore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Ecore"))

    if not (pcore_dirs and ecore_dirs):
        print(f"Skipping {application_name}: Missing log files.")
        #continue

    # Take the first matching directory (assuming there's only one result per application)
    pcore_file = os.path.join(pcore_dirs[0], "periodic_counters.log")
    ecore_file = os.path.join(ecore_dirs[0], "periodic_counters.log")

    # Ensure the log files exist
    if not (os.path.exists(pcore_file) and os.path.exists(ecore_file)):
        print(f"Skipping {application_name}: Missing log files.")
        #continue

    # Define the size of the instruction slice (e.g., 2e9 instructions)
    instruction_slice = 1e9

    # Process for each energy type
    for energy_type in ["psys",]:
        # Generate the lookup table
        lookup_table = generate_lookup_table(application_name, pcore_file, ecore_file, instruction_slice, energy_type)
        #print(lookup_table)
        all_lookup_tables.extend(lookup_table)
        
        # Generate the energy efficiency plot
        generate_efficiency_plot(application_name, lookup_table, pcore_file, ecore_file, output_directory, energy_type, instruction_slice, frequency_raw)

    # Convert all lookup tables to a DataFrame and save as one CSV
    #lookup_df = pd.DataFrame(all_lookup_tables)
    #lookup_df.to_csv(os.path.join(output_directory, "all_applications_lookup_table.csv"), index=False)

if __name__ == "__main__":
    main()
