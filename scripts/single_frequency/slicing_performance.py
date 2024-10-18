import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import glob
import sys

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
            if "PID" in line:
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
# Updated generate_lookup_table function with boundary checks
def generate_lookup_table(application_name, pcore_file, ecore_file, instruction_slice):
    # Parse the logs for instructions and energy
    pcore_time, pcore_instr = parse_log_file(pcore_file)
    ecore_time, ecore_instr = parse_log_file(ecore_file)

    # Printing the application name and the number of instructions
    #print(f"Application: {application_name}\t[E-Core] Insts= {ecore_instr[-1]:.2e}\t Time={ecore_time[-1]:.2f}s\t [P-Core] Insts= {pcore_instr[-1]:.2e}\t Time={pcore_time[-1]:.2f}s")
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
        #print(f"Slice: {current_instr:.2e} - {next_instr:.2e} instructions")
        if pcore_end_time >= pcore_time[-1]:
            #print("Ignoring this slice as it exceeds the P-core log duration")
            break
        else:
            #print(f"\tE-core: {ecore_start_time:.2f}s - {ecore_end_time:.2f}s")
            #print(f"\tP-core: {pcore_start_time:.2f}s - {pcore_end_time:.2f}s")
            # Calculate the duration of the slice on each core
            ecore_duration = ecore_end_time - ecore_start_time
            pcore_duration = pcore_end_time - pcore_start_time

            duration_improvement = ((ecore_duration - pcore_duration) / pcore_duration) * 100
            # Record the results
            lookup_table.append({
                "Application": application_name,
                "Instruction Start": current_instr,
                "Instruction End": next_instr,
                "E-core Duration (s)": ecore_duration,
                "P-core Duration (s)": pcore_duration,
                "E-core Duration Improvement (%)": duration_improvement
            })
        current_instr = next_instr

    return lookup_table



def generate_efficiency_plot(application_name, lookup_table_filtered, pcore_file, ecore_file, output_directory):
    # Parse the logs again for detailed plotting
    pcore_time, pcore_instr = parse_log_file(pcore_file)
    ecore_time, ecore_instr = parse_log_file(ecore_file)

    # Calculate periodic instructions (difference between consecutive instruction counts)
    pcore_periodic_instr = np.diff([0] + pcore_instr)
    ecore_periodic_instr = np.diff([0] + ecore_instr)

    #print(application_name)
    #print(lookup_table_filtered)
    #print(pcore_periodic_instr)
    #print(ecore_periodic_instr)
    # Identify the phases with the maximum and minimum energy efficiency improvement
    max_improvement_index = max(range(len(lookup_table_filtered)), key=lambda i: lookup_table_filtered[i]['E-core Duration Improvement (%)'])
    min_improvement_index = min(range(len(lookup_table_filtered)), key=lambda i: lookup_table_filtered[i]['E-core Duration Improvement (%)'])
    
    # Create subplots (2x1 layout for E-core and P-core)
    fig, axs = plt.subplots(2, 1, figsize=(14, 12), sharex=True)

    # Colors for the phases
    colors = plt.cm.viridis(np.linspace(0, 1, len(lookup_table_filtered)))

    ### E-core Plot ###
    # Plot cumulative instructions for E-core
    axs[0].plot(ecore_time, ecore_instr, color="red", label="Cumulative Instructions")
    axs[0].set_ylabel("Cumulative Instructions")
    axs[0].set_title(f"{application_name} - E-core Phase Duration")

    # Plot periodic instructions for E-core
    ax2 = axs[0].twinx()
    ax2.plot(ecore_time, ecore_periodic_instr, color="orange", label="Periodic Instructions", alpha=0.7)
    ax2.set_ylabel("Periodic Instructions")

    # Highlight phases for E-core and add slice number and percentage improvement annotations
    for i, row in enumerate(lookup_table_filtered):
        # Find start and end times for the current instruction slice
        start_instr = row['Instruction Start']
        end_instr = row['Instruction End']

        # Find corresponding times using searchsorted
        start_index = np.searchsorted(ecore_instr, start_instr)
        end_index = np.searchsorted(ecore_instr, end_instr)

        # Ensure indices are within range
        start_index = min(start_index, len(ecore_time) - 1)
        end_index = min(end_index, len(ecore_time) - 1)

        start_time = ecore_time[start_index]
        end_time = ecore_time[end_index]

        # Determine the highlight color and alpha
        if i == max_improvement_index:
            highlight_alpha = 0.5
            highlight_color = 'gold'
        elif i == min_improvement_index:
            highlight_alpha = 0.5
            highlight_color = 'lightcoral'
        else:
            highlight_alpha = 0.3
            highlight_color = colors[i]

        # Highlight the phase
        axs[0].axvspan(
            start_time,
            end_time,
            color=highlight_color,
            alpha=highlight_alpha,
            edgecolor=None,
            linewidth=2 if i in [max_improvement_index, min_improvement_index] else 0
        )

        # Calculate the position for the annotation
        annotation_time = (start_time + end_time) / 2
        annotation_instr = (start_instr + end_instr) / 2

        # Add text annotation for the slice number and percentage improvement on separate lines
        improvement_text = f"P{i+1}\n{row['E-core Duration Improvement (%)']:.2f}%"
        axs[0].text(
            annotation_time,
            annotation_instr,
            improvement_text,
            color="black",
            ha="center",
            va="center",
            fontsize=8,
            bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1)
        )

    ### P-core Plot ###
    # Plot cumulative instructions for P-core
    axs[1].plot(pcore_time, pcore_instr, color="blue", label="Cumulative Instructions")
    axs[1].set_xlabel("Time (s)")
    axs[1].set_ylabel("Cumulative Instructions")
    axs[1].set_title(f"{application_name} - P-core Phase Duration)")

    # Plot periodic instructions for P-core
    ax3 = axs[1].twinx()
    ax3.plot(pcore_time, pcore_periodic_instr, color="yellow", label="Periodic Instructions", alpha=0.7)
    ax3.set_ylabel("Periodic Instructions")

    # Highlight phases for P-core and add slice number and percentage improvement annotations
    for i, row in enumerate(lookup_table_filtered):
        # Find start and end times for the current instruction slice
        start_instr = row['Instruction Start']
        end_instr = row['Instruction End']

        # Find corresponding times using searchsorted
        start_index = np.searchsorted(pcore_instr, start_instr)
        end_index = np.searchsorted(pcore_instr, end_instr)

        # Ensure indices are within range
        start_index = min(start_index, len(pcore_time) - 1)
        end_index = min(end_index, len(pcore_time) - 1)

        start_time = pcore_time[start_index]
        end_time = pcore_time[end_index]

        # Determine the highlight color and alpha
        if i == max_improvement_index:
            highlight_alpha = 0.5
            highlight_color = 'gold'
        elif i == min_improvement_index:
            highlight_alpha = 0.5
            highlight_color = 'lightcoral'
        else:
            highlight_alpha = 0.3
            highlight_color = colors[i]

        # Highlight the phase
        axs[1].axvspan(
            start_time,
            end_time,
            color=highlight_color,
            alpha=highlight_alpha,
            edgecolor=None,
            linewidth=2 if i in [max_improvement_index, min_improvement_index] else 0
        )

        # Calculate the position for the annotation
        annotation_time = (start_time + end_time) / 2
        annotation_instr = (start_instr + end_instr) / 2

        # Add text annotation for the slice number and percentage improvement on separate lines
        improvement_text = f"P{i+1}\n{row['E-core Duration Improvement (%)']:.2f}%"
        axs[1].text(
            annotation_time,
            annotation_instr,
            improvement_text,
            color="black",
            ha="center",
            va="center",
            fontsize=8,
            bbox=dict(facecolor='white', alpha=0.6, edgecolor='none', pad=1)
        )

    # Add legends
    axs[0].legend(loc="upper left")
    ax2.legend(loc="upper right")
    axs[1].legend(loc="upper left")
    ax3.legend(loc="upper right")

    # Adjust layout for better spacing
    plt.tight_layout()

    # Save the plot
    plt.savefig(os.path.join(output_directory, f"{application_name}_execution_phases.png"))
    plt.close()


# Main script to process all applications
def main():
    # Ensure the output directory exists

    log_directory = config.RESULTS_FOLDER

    frequency = "2500MHz"

    
    output_directory = os.path.join(config.ROOTPATH, f"{log_directory}/plots/performance_phases/{frequency}")
    os.makedirs(output_directory, exist_ok=True)

    all_lookup_tables = []

    for application_name in config.parsec_apps:
        # Use glob to find the directories matching the application name for P-core and E-core at 2000MHz
        pcore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Pcore"))
        ecore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Ecore"))

        if not (pcore_dirs and ecore_dirs):
            print(f"Skipping {application_name}: Missing log files.")
            continue

        # Take the first matching directory (assuming there's only one result per application)
        pcore_file = os.path.join(pcore_dirs[0], "periodic_counters.log")
        ecore_file = os.path.join(ecore_dirs[0], "periodic_counters.log")

        # Ensure the log files exist
        if not (os.path.exists(pcore_file) and os.path.exists(ecore_file)):
            print(f"Skipping {application_name}: Missing log files.")
            continue

        # Define the size of the instruction slice (e.g., 2e9 instructions)
        instruction_slice = 2e9

        lookup_table = generate_lookup_table(application_name, pcore_file, ecore_file, instruction_slice)
            #print(lookup_table)
        all_lookup_tables.extend(lookup_table)
            
            # Generate the energy efficiency plot
        generate_efficiency_plot(application_name, lookup_table, pcore_file, ecore_file, output_directory)

    # Convert all lookup tables to a DataFrame and save as one CSV
    lookup_df = pd.DataFrame(all_lookup_tables)
    #lookup_df.to_csv(os.path.join(output_directory, "all_applications_lookup_table.csv"), index=False)

if __name__ == "__main__":
    main()
