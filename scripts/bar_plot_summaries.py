import os
import re
import glob
import sys
import numpy as np
import matplotlib.pyplot as plt

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import config

# Function to parse log file and accumulate instructions and energy
def parse_log_file(log_file, energy_type):
    time_points = []
    cumulative_instructions = []
    cumulative_energy = []

    with open(log_file, 'r') as file:
        cumulative_instr = 0
        cumulative_energy_value = 0
        for line in file:
            time_match = re.search(r'\[(\d+\.\d+)s\]', line)
            instr_match = re.search(r'instructions = (\d+)', line)
            energy_match = re.search(rf'power/energy-{energy_type}/ = (\d+)', line)

            if time_match and instr_match and energy_match:
                time = float(time_match.group(1))
                instructions = int(instr_match.group(1))
                energy = int(energy_match.group(1))

                cumulative_instr += instructions
                cumulative_energy_value += energy

                time_points.append(time)
                cumulative_instructions.append(cumulative_instr)
                cumulative_energy.append(cumulative_energy_value)
    
    return time_points, cumulative_instructions, cumulative_energy

# Function to gather metrics for each application at a given frequency and energy type
def gather_metrics(application_name, frequency, energy_type):
    log_directory = config.RESULTS_FOLDER

    # Use glob to find the directories matching the application name for P-core and E-core at the specified frequency
    pcore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Pcore"))
    ecore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Ecore"))

    if not (pcore_dirs and ecore_dirs):
        return None

    # Take the first matching directory (assuming there's only one result per application)
    pcore_file = os.path.join(pcore_dirs[0], "periodic_counters.log")
    ecore_file = os.path.join(ecore_dirs[0], "periodic_counters.log")

    # Parse the logs
    ecore_time, ecore_instr, ecore_energy = parse_log_file(ecore_file, energy_type)
    pcore_time, pcore_instr, pcore_energy = parse_log_file(pcore_file, energy_type)

    # Calculate metrics for E-core
    ecore_total_time = ecore_time[-1]
    ecore_total_energy = ecore_energy[-1]
    ecore_total_instructions = ecore_instr[-1]

    # Calculate metrics for P-core
    pcore_total_time = pcore_time[-1]
    pcore_total_energy = pcore_energy[-1]
    pcore_total_instructions = pcore_instr[-1]

    # Calculate the average number of instructions executed
    avg_instructions = (ecore_total_instructions + pcore_total_instructions) / 2

    # Calculate energy efficiency using the average instructions
    ecore_efficiency = (avg_instructions / ecore_total_energy) / 1e6 if ecore_total_energy > 0 else np.nan
    pcore_efficiency = (avg_instructions / pcore_total_energy) / 1e6 if pcore_total_energy > 0 else np.nan

    return {
        'ecore_time': ecore_total_time,
        'pcore_time': pcore_total_time,
        'ecore_energy': ecore_total_energy,
        'pcore_energy': pcore_total_energy,
        'ecore_efficiency': ecore_efficiency,
        'pcore_efficiency': pcore_efficiency
    }

# Function to calculate percentage difference and add annotations
def annotate_bars(ax, ecore_values, pcore_values, index, bar_width):
    for i in range(len(ecore_values)):
        if pcore_values[i] > 0:
            percentage_diff = ((ecore_values[i] - pcore_values[i]) / pcore_values[i]) * 100
            annotation = f"{percentage_diff:.1f}%"
            ax.text(index[i] + bar_width / 2, max(ecore_values[i], pcore_values[i]) * 1.01, annotation,
                    ha='center', va='bottom', fontsize=8, color='black')

# Function to generate the execution time plot
def plot_execution_time(applications, ecore_times, pcore_times, frequency, output_dir):
    plt.figure(figsize=(10, 6))
    bar_width = 0.35
    index = np.arange(len(applications))
    
    bars1 = plt.bar(index, ecore_times, bar_width, label='E-core', color='red', alpha=0.7)
    bars2 = plt.bar(index + bar_width, pcore_times, bar_width, label='P-core', color='blue', alpha=0.7)
    
    plt.xlabel('Applications')
    plt.ylabel('Execution Time (s)')
    plt.title(f'Execution Time at {frequency}')
    plt.xticks(index + bar_width / 2, applications, rotation=45, ha="right")
    plt.legend()

    # Annotate the bars with percentage differences
    annotate_bars(plt, ecore_times, pcore_times, index, bar_width)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"execution_time_{frequency}.png"))
    plt.close()

# Function to generate energy plots for each energy type
def plot_energy(applications, ecore_values, pcore_values, metric_name, frequency, energy_type, output_dir):
    plt.figure(figsize=(10, 6))
    bar_width = 0.35
    index = np.arange(len(applications))
    
    bars1 = plt.bar(index, ecore_values, bar_width, label='E-core', color='red', alpha=0.7)
    bars2 = plt.bar(index + bar_width, pcore_values, bar_width, label='P-core', color='blue', alpha=0.7)
    
    plt.xlabel('Applications')
    plt.ylabel(f'{metric_name} ({energy_type.capitalize()})')
    plt.title(f'{metric_name} at {frequency} ({energy_type})')
    plt.xticks(index + bar_width / 2, applications, rotation=45, ha="right")
    plt.legend()

    # Annotate the bars with percentage differences
    annotate_bars(plt, ecore_values, pcore_values, index, bar_width)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{metric_name.lower()}_{energy_type}_{frequency}.png"))
    plt.close()

# Main function to create all plots
def main():
    energy_types = ["pkg", "psys", "cores"]
    #frequencies = ["1500MHz", "2000MHz", "2500MHz", "3000MHz", "3500MHz"]
    #frequencies = ["2500MHz", "3500MHz"]
    frequencies = ["3500MHz",]
    
    output_dir = os.path.join(config.ROOTPATH, f"{config.RESULTS_FOLDER}/plots/bars")
    os.makedirs(output_dir, exist_ok=True)

    for frequency in frequencies:
        applications = []
        ecore_times = []
        pcore_times = []
        ecore_energy = {et: [] for et in energy_types}
        pcore_energy = {et: [] for et in energy_types}
        ecore_efficiency = {et: [] for et in energy_types}
        pcore_efficiency = {et: [] for et in energy_types}

        for application_name in config.splash2_apps:
            # Gather execution time
            metrics = gather_metrics(application_name, frequency, energy_types[0])  # Any energy type works for time
            if metrics is None:
                continue

            applications.append(application_name)
            ecore_times.append(metrics['ecore_time'])
            pcore_times.append(metrics['pcore_time'])

            # Gather energy and efficiency metrics
            for energy_type in energy_types:
                metrics = gather_metrics(application_name, frequency, energy_type)
                ecore_energy[energy_type].append(metrics['ecore_energy'])
                pcore_energy[energy_type].append(metrics['pcore_energy'])
                ecore_efficiency[energy_type].append(metrics['ecore_efficiency'])
                pcore_efficiency[energy_type].append(metrics['pcore_efficiency'])

        # Generate plots
        plot_execution_time(applications, ecore_times, pcore_times, frequency, output_dir)
        for energy_type in energy_types:
            plot_energy(applications, ecore_energy[energy_type], pcore_energy[energy_type], 'Energy Consumption', frequency, energy_type, output_dir)
            plot_energy(applications, ecore_efficiency[energy_type], pcore_efficiency[energy_type], 'Energy Efficiency', frequency, energy_type, output_dir)

if __name__ == "__main__":
    main()
