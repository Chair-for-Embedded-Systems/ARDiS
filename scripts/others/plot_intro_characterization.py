import os
import re
import glob
import sys
import numpy as np
import matplotlib.pyplot as plt

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
import ardis.config as config

# Function to parse periodic log and accumulate instructions and energy
def parse_periodic_log(log_file):
    total_instructions = 0
    total_energy = 0
    all_energies = []
    all_instructions = []
    all_efficiencies = []

    with open(log_file, 'r') as file:
        for line in file:
            # Check for PID entries and accumulate instructions
            pid_match = re.search(r'PID \d+: instructions = (\d+)', line)
            if pid_match:
                instructions = int(pid_match.group(1))
                total_instructions += instructions
                all_instructions.append(instructions)

            # Check for SYSTEM entries and accumulate energy (for energy-psys)
            energy_match = re.search(r'power/energy-psys/ = (\d+\.\d+)', line)
            if energy_match:
                energy = float(energy_match.group(1))
                all_energies.append(energy)
                total_energy += energy
    all_efficiencies = [((instructions / energy) * 1e-6) for instructions, energy in zip(all_instructions, all_energies)]
    return total_instructions, total_energy, np.mean(all_energies), np.mean(all_efficiencies)

# Function to parse the execution log and retrieve cumulative instructions, energy, and time
def parse_execution_log(log_file):
    total_time = None
    total_energy = None
    total_instructions = None
    cumulative_instructions = None

    with open(log_file, 'r') as file:
        for line in file:
            if "Total time elapsed (perf)=" in line:
                total_time = float(re.search(r'Total time elapsed \(perf\)= (\d+\.\d+)', line).group(1))
            if "Total instructions executed =" in line:
                total_instructions = int(re.search(r'Total instructions executed = (\d+)', line).group(1))
            if "Total energy consumed (perf)=" in line:
                total_energy = float(re.search(r'Total energy consumed \(perf\)= (\d+\.\d+)', line).group(1))
            # Capture the last "Cumulative Instructions" entry
            cumulative_match = re.search(r'Cumulative Instructions = (\d+)', line)
            if cumulative_match:
                cumulative_instructions = int(cumulative_match.group(1))
    
    return total_time, total_instructions, total_energy, cumulative_instructions

# Function to compute IPJ (instructions per joule)
def compute_ipj(instructions, energy):
    return (instructions / energy) * 1e-6 if energy > 0 else np.nan

# Function to gather metrics for an application
def gather_metrics(application_name, frequencies):
    # Paths for periodic and execution logs
    pcore_dirs = [glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{freq}MHz_Pcore")) for freq in frequencies]
    ecore_dirs = [glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{freq}MHz_Ecore")) for freq in frequencies]

    if not (pcore_dirs and ecore_dirs):
        return None
    print(pcore_dirs)
    print(ecore_dirs)
    # Assume both log files are named as follows:
    periodic_log_name = "periodic_counters.log"
    execution_log_name = "execution.log"

    # Initialize a dictionary to hold all the retrieved data
    metrics = {
        'periodic': {},
        'execution': {}
    }

    # Parse the periodic logs for each frequency on P-cores and E-cores
    for i, freq in enumerate(frequencies):
        pcore_periodic_file = os.path.join(pcore_dirs[i][0], periodic_log_name)
        ecore_periodic_file = os.path.join(ecore_dirs[i][0], periodic_log_name)

        pcore_instructions, pcore_energy, _, _ = parse_periodic_log(pcore_periodic_file)
        ecore_instructions, ecore_energy, _, _ = parse_periodic_log(ecore_periodic_file)
        
        metrics['periodic'][f'pcore_{freq}'] = {'instructions': pcore_instructions, 'energy': pcore_energy}
        metrics['periodic'][f'ecore_{freq}'] = {'instructions': ecore_instructions, 'energy': ecore_energy}

    # Parse the execution logs for each frequency on P-cores and E-cores
    for i, freq in enumerate(frequencies):
        pcore_execution_file = os.path.join(pcore_dirs[i][0], execution_log_name)
        ecore_execution_file = os.path.join(ecore_dirs[i][0], execution_log_name)

        pcore_time, pcore_total_instructions, pcore_energy, _ = parse_execution_log(pcore_execution_file)
        ecore_time, ecore_total_instructions, ecore_energy, _ = parse_execution_log(ecore_execution_file)

        metrics['execution'][f'pcore_{freq}'] = {'instructions': pcore_total_instructions, 'energy': pcore_energy, 'time': pcore_time}
        metrics['execution'][f'ecore_{freq}'] = {'instructions': ecore_total_instructions, 'energy': ecore_energy, 'time': ecore_time}
    #print(metrics)
    return metrics

def compute_metrics_for_all(applications, frequencies):
    metric_data = {}

    for application in applications:
        print(application)
        metrics = gather_metrics(application, frequencies)
        if metrics is None:
            print(f"Metrics not found for {application}")
            continue

        # Initialize an application dictionary in metric_data
        metric_data[application] = {
            'execution': {},
            'periodic': {}
        }

        # Metric 1: Instantaneous IPJ (Mean Efficiency)
        pcore_ipjs_1 = [compute_ipj(metrics['periodic'][f'pcore_{freq}']['instructions'], metrics['periodic'][f'pcore_{freq}']['energy']) for freq in frequencies]
        ecore_ipjs_1 = [compute_ipj(metrics['periodic'][f'ecore_{freq}']['instructions'], metrics['periodic'][f'ecore_{freq}']['energy']) for freq in frequencies]

        # Add the IPJ data to 'periodic' section
        metric_data[application]['periodic']['pcore_ipjs'] = pcore_ipjs_1
        metric_data[application]['periodic']['ecore_ipjs'] = ecore_ipjs_1

        # You may also need to structure 'execution' data similarly to what you're expecting
        for freq in frequencies:
            metric_data[application]['execution'][f'pcore_{freq}'] = metrics['execution'][f'pcore_{freq}']
            metric_data[application]['execution'][f'ecore_{freq}'] = metrics['execution'][f'ecore_{freq}']

    return metric_data



def plot_subfigures(metric_data, applications, frequencies, fixed_frequency):
    """
    Generate a plot with three rectangular subfigures for execution time, energy, and energy efficiency.
    """
    # Extract index of the fixed frequency
    fixed_freq_index = frequencies.index(fixed_frequency)
    
    # Initialize lists to store the metrics for plotting
    execution_times = {'P Core': [], 'E Core': []}
    energies = {'P Core': [], 'E Core': []}
    efficiencies = {'P Core': [], 'E Core': []}

    # Populate the lists with the data for each application at the fixed frequency
    for app in applications:
        execution_times['P Core'].append(metric_data[app]['execution'][f'pcore_{fixed_frequency}']['time'])
        execution_times['E Core'].append(metric_data[app]['execution'][f'ecore_{fixed_frequency}']['time'])
        
        energies['P Core'].append(metric_data[app]['execution'][f'pcore_{fixed_frequency}']['energy'])
        energies['E Core'].append(metric_data[app]['execution'][f'ecore_{fixed_frequency}']['energy'])
        
        efficiencies['P Core'].append(compute_ipj(
            metric_data[app]['execution'][f'pcore_{fixed_frequency}']['instructions'], 
            metric_data[app]['execution'][f'pcore_{fixed_frequency}']['energy']
        ))
        efficiencies['E Core'].append(compute_ipj(
            metric_data[app]['execution'][f'ecore_{fixed_frequency}']['instructions'], 
            metric_data[app]['execution'][f'ecore_{fixed_frequency}']['energy']
        ))

    # Create subplots
    fig, axes = plt.subplots(3, 1, figsize=(6, 18))

    # X-axis positions for the applications
    indices = np.arange(len(applications))
    bar_width = 0.35

    # Plot execution times
    axes[0].bar(indices - bar_width/2, execution_times['P Core'], bar_width, label='P Core')
    axes[0].bar(indices + bar_width/2, execution_times['E Core'], bar_width, label='E Core')
    axes[0].set_xlabel('Applications')
    axes[0].set_ylabel('Execution Time (s)')
    axes[0].set_title(f'Execution Time at {fixed_frequency} MHz')
    axes[0].set_xticks(indices)
    axes[0].set_xticklabels(applications, rotation=45, ha='right')
    axes[0].legend()

    # Plot energies
    axes[1].bar(indices - bar_width/2, energies['P Core'], bar_width, label='P Core')
    axes[1].bar(indices + bar_width/2, energies['E Core'], bar_width, label='E Core')
    axes[1].set_xlabel('Applications')
    axes[1].set_ylabel('Energy (Joules)')
    axes[1].set_title(f'Energy Consumption at {fixed_frequency} MHz')
    axes[1].set_xticks(indices)
    axes[1].set_xticklabels(applications, rotation=45, ha='right')
    axes[1].legend()

    # Plot energy efficiency (IPJ)
    axes[2].bar(indices - bar_width/2, efficiencies['P Core'], bar_width, label='P Core')
    axes[2].bar(indices + bar_width/2, efficiencies['E Core'], bar_width, label='E Core')
    axes[2].set_xlabel('Applications')
    axes[2].set_ylabel('Energy Efficiency (IPJ)')
    axes[2].set_title(f'Energy Efficiency at {fixed_frequency} MHz')
    axes[2].set_xticks(indices)
    axes[2].set_xticklabels(applications, rotation=45, ha='right')
    axes[2].legend()

    # Annotate the bars with percentage improvement
    for ax in axes:
        for i, rect in enumerate(ax.patches):
            height = rect.get_height()
            if i % 2 == 0:
                ax.annotate(f'{(height - ax.patches[i+1].get_height()) / ax.patches[i+1].get_height() * 100:.2f}%', 
                            xy=(rect.get_x() + rect.get_width() / 2, height), 
                            xytext=(0, 3),  # 3 points vertical offset
                            textcoords="offset points",
                            ha='center', va='bottom')

    # Adjust layout to prevent overlap
    plt.tight_layout()

    # Save the plot to the output directory
    plot_file = os.path.join(config.PAPERPLOT_FOLDER, f'three_metrics_at_{fixed_frequency}MHz.png')
    plt.savefig(plot_file)
    plt.close()

    print(f"Plot with subfigures saved as {plot_file}")


def main():
    #applications = config.parsec_apps
    applications = np.random.choice(config.parsec_apps, 10, replace=False)
    frequencies = ["2500", ]  # Example frequencies
    fixed_frequency = "2500"  # Example fixed frequency

    # Compute metrics
    metric1_data = compute_metrics_for_all(applications, frequencies)
    #print(metric1_data)
    # Plot the subfigures for execution time, energy, and energy efficiency at the fixed frequency
    plot_subfigures(metric1_data, applications, frequencies, fixed_frequency)
        

if __name__ == "__main__":
    main()