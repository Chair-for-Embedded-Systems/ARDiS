import os
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import glob
import sys

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


def generate_lookup_table(application_name, pcore_file, ecore_file, instruction_slice, energy_type):
    # Parse the logs for instructions and energy
    pcore_time, pcore_instr = parse_log_file(pcore_file)
    ecore_time, ecore_instr = parse_log_file(ecore_file)
    pcore_energy_time, pcore_energy = extract_cumulative_energy(pcore_file, energy_type)
    ecore_energy_time, ecore_energy = extract_cumulative_energy(ecore_file, energy_type)

    # Initialize the lookup table
    lookup_table = []

    # Debugging: Print the lengths of the parsed data
    print(f"Debug: {application_name} - Energy Type: {energy_type}")
    print(f"pcore_time length: {len(pcore_time)}, pcore_instr length: {len(pcore_instr)}")
    print(f"ecore_time length: {len(ecore_time)}, ecore_instr length: {len(ecore_instr)}")
    print(f"pcore_energy length: {len(pcore_energy)}, ecore_energy length: {len(ecore_energy)}")

    # Process the E-core first
    ecore_index = 0
    pcore_index = 0
    current_instr = 0
    
    while current_instr < ecore_instr[-1]:
        next_instr = current_instr + instruction_slice

        # Debugging: Print current instruction slice range
        #print(f"Debug: Processing instruction range {current_instr} to {next_instr}")

        # Find the start time and energy on the E-core
        ecore_start_time = ecore_time[ecore_index]
        ecore_start_energy = ecore_energy[ecore_index]

        # Find the time and energy on the E-core where this slice ends
        while ecore_index < len(ecore_instr) and ecore_instr[ecore_index] < next_instr:
            ecore_index += 1
        ecore_end_time = ecore_time[ecore_index] if ecore_index < len(ecore_instr) else ecore_time[-1]
        ecore_end_energy = ecore_energy[ecore_index] if ecore_index < len(ecore_energy) else ecore_energy[-1]

        # Debugging: Print E-core indices and times
        #print(f"Debug: E-core start index: {ecore_index}, start time: {ecore_start_time}, end time: {ecore_end_time}")

        # Find the start time and energy on the P-core
        if pcore_index < len(pcore_time):
            pcore_start_time = pcore_time[pcore_index]
            pcore_start_energy = pcore_energy[pcore_index]
        else:
            print(f"Error: pcore_index {pcore_index} out of range for pcore_time (length: {len(pcore_time)})")
            break

        # Find corresponding time and energy on P-core
        while pcore_index < len(pcore_instr) and pcore_instr[pcore_index] < next_instr:
            pcore_index += 1
        if pcore_index < len(pcore_time):
            pcore_end_time = pcore_time[pcore_index]
            pcore_end_energy = pcore_energy[pcore_index]
        else:
            print(f"Error: pcore_index {pcore_index} out of range for pcore_time (length: {len(pcore_time)})")
            break

        # Debugging: Print P-core indices and times
        #print(f"Debug: P-core start index: {pcore_index}, start time: {pcore_start_time}, end time: {pcore_end_time}")

        # Calculate the duration of the slice on each core
        ecore_duration = ecore_end_time - ecore_start_time
        pcore_duration = pcore_end_time - pcore_start_time

        # Calculate energy consumed during the phase
        ecore_energy_consumed = ecore_end_energy - ecore_start_energy
        pcore_energy_consumed = pcore_end_energy - pcore_start_energy

        if ecore_energy_consumed <= 0:
            print(f"Debug: E-core zero or negative energy consumption at slice {current_instr} to {next_instr}, start energy: {ecore_start_energy}, end energy: {ecore_end_energy}")
        if pcore_energy_consumed <= 0:
            print(f"Debug: P-core zero or negative energy consumption at slice {current_instr} to {next_instr}, start energy: {pcore_start_energy}, end energy: {pcore_end_energy}")


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



def generate_efficiency_plot(application_name, lookup_table, pcore_file, ecore_file, output_directory, energy_type):
    # Parse the logs again for detailed plotting
    pcore_time, pcore_instr = parse_log_file(pcore_file)
    ecore_time, ecore_instr = parse_log_file(ecore_file)

    # Calculate periodic instructions (difference between consecutive instruction counts)
    pcore_periodic_instr = np.diff([0] + pcore_instr)
    ecore_periodic_instr = np.diff([0] + ecore_instr)

    # Filter the lookup table for the current energy type
    lookup_table_filtered = [row for row in lookup_table if row['Energy Type'] == energy_type]

    # Handle the case when lookup_table_filtered is empty
    if not lookup_table_filtered:
        print(f"No data available for {application_name} with energy type {energy_type}. Skipping plot generation.")
        return  # Exit the function early


    # Identify the phases with the maximum and minimum energy efficiency improvement
    max_improvement_index = max(range(len(lookup_table_filtered)), key=lambda i: lookup_table_filtered[i]['E-core Efficiency Improvement (%)'])
    min_improvement_index = min(range(len(lookup_table_filtered)), key=lambda i: lookup_table_filtered[i]['E-core Efficiency Improvement (%)'])
    
    # Create subplots (2x1 layout for E-core and P-core)
    fig, axs = plt.subplots(2, 1, figsize=(14, 12), sharex=True)

    # Colors for the phases
    colors = plt.cm.viridis(np.linspace(0, 1, len(lookup_table_filtered)))

    ### E-core Plot ###
    # Plot cumulative instructions for E-core
    axs[0].plot(ecore_time, ecore_instr, color="red", label="Cumulative Instructions")
    axs[0].set_ylabel("Cumulative Instructions")
    axs[0].set_title(f"{application_name} - E-core Energy Efficiency and Phases ({energy_type})")

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
        improvement_text = f"P{i+1}\n{row['E-core Efficiency Improvement (%)']:.2f}%"
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
    axs[1].set_title(f"{application_name} - P-core Energy Efficiency and Phases ({energy_type})")

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
        improvement_text = f"P{i+1}\n{row['E-core Efficiency Improvement (%)']:.2f}%"
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
    plt.savefig(os.path.join(output_directory, f"{application_name}_efficiency_phases_{energy_type}.png"))
    plt.close()


# Main script to process all applications
def main():
    # Ensure the output directory exists

    log_directory = config.RESULTS_FOLDER

    frequency = "2500MHz"

    
    output_directory = os.path.join(config.ROOTPATH, f"{log_directory}/plots/energy_efficiency_phases/{frequency}")
    os.makedirs(output_directory, exist_ok=True)

    all_lookup_tables = []

    for application_name in config.spec_apps:
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
        instruction_slice = 2e10

        # Process for each energy type
        for energy_type in ["cores", "pkg", "psys"]:
            # Generate the lookup table
            lookup_table = generate_lookup_table(application_name, pcore_file, ecore_file, instruction_slice, energy_type)
            #print(lookup_table)
            all_lookup_tables.extend(lookup_table)
            
            # Generate the energy efficiency plot
            generate_efficiency_plot(application_name, lookup_table, pcore_file, ecore_file, output_directory, energy_type)

    # Convert all lookup tables to a DataFrame and save as one CSV
    lookup_df = pd.DataFrame(all_lookup_tables)
    lookup_df.to_csv(os.path.join(output_directory, "all_applications_lookup_table.csv"), index=False)

if __name__ == "__main__":
    main()
