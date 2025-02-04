import os
import re
import glob
import sys
import numpy as np
import matplotlib.pyplot as plt

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

# Function to parse periodic log and accumulate instructions, energy, and capture execution time
def parse_periodic_log(log_file):
    total_instructions = 0
    total_energy = 0
    first_timestamp = None
    last_timestamp = None

    with open(log_file, 'r') as file:
        for line in file:
            # Check for timestamp
            timestamp_match = re.search(r'\[(\d+\.\d+)s\]', line)
            if timestamp_match:
                timestamp = float(timestamp_match.group(1))
                if first_timestamp is None:
                    first_timestamp = timestamp
                last_timestamp = timestamp

            # Check for PID entries and accumulate instructions
            pid_match = re.search(r'PID \d+: instructions = (\d+)', line)
            if pid_match:
                instructions = int(pid_match.group(1))
                total_instructions += instructions

            # Check for SYSTEM entries and accumulate energy (for energy-pkg)
            energy_match = re.search(r'power/energy-psys/ = (\d+\.\d+)', line)
            if energy_match:
                energy = float(energy_match.group(1))
                total_energy += energy

    # Calculate total execution time based on the first and last timestamps
    total_time = None
    if first_timestamp is not None and last_timestamp is not None:
        total_time = last_timestamp - first_timestamp

    return total_instructions, total_energy, total_time

# Function to parse the one-shot execution log and retrieve cumulative instructions, energy, and time
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

# Function to compute Energy Delay Product (EDP)
def compute_edp(energy, time):
    if energy is None or time is None:
        return None
    return energy * time
# Function to gather metrics for P-core, Mixed-core, and all governors from both periodic and execution logs
def gather_metrics(application_name, frequency, governors):
    # Paths for periodic and execution logs
    pcore_dirs = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{frequency}_Pcore"))
    mixed_dirs = glob.glob(os.path.join(config.PARSEC_MIXED_STATIC_FOLDER_5E9_EDP, f"*_{application_name}_Mixed"))

    if not (pcore_dirs and mixed_dirs):
        return None

    # Assume both log files are named as follows:
    periodic_log_name = "periodic_counters.log"
    execution_log_name = "execution.log"

    # Initialize a dictionary to hold all the retrieved data
    metrics = {
        'periodic': {
            'pcore_instructions': None,
            'pcore_energy': None,
            'pcore_time': None,
            'mixed_instructions': None,
            'mixed_energy': None,
            'mixed_time': None,
            'governors': {}
        },
        'execution': {
            'pcore_cumulative_instructions': None,
            'pcore_total_instructions': None,
            'pcore_total_energy': None,
            'pcore_total_time': None,
            'mixed_cumulative_instructions': None,
            'mixed_total_instructions': None,
            'mixed_total_energy': None,
            'mixed_total_time': None,
            'governors': {}
        }
    }

    # Parse the periodic logs
    pcore_periodic_file = os.path.join(pcore_dirs[0], periodic_log_name)
    mixed_periodic_file = os.path.join(mixed_dirs[0], periodic_log_name)

    pcore_periodic_instructions, pcore_periodic_energy, pcore_periodic_time = parse_periodic_log(pcore_periodic_file)
    mixed_periodic_instructions, mixed_periodic_energy, mixed_periodic_time = parse_periodic_log(mixed_periodic_file)

    metrics['periodic']['pcore_instructions'] = pcore_periodic_instructions
    metrics['periodic']['pcore_energy'] = pcore_periodic_energy
    metrics['periodic']['pcore_time'] = pcore_periodic_time
    metrics['periodic']['mixed_instructions'] = mixed_periodic_instructions
    metrics['periodic']['mixed_energy'] = mixed_periodic_energy
    metrics['periodic']['mixed_time'] = mixed_periodic_time

    # Parse the execution logs
    pcore_execution_file = os.path.join(pcore_dirs[0], execution_log_name)
    mixed_execution_file = os.path.join(mixed_dirs[0], execution_log_name)

    pcore_execution_time, pcore_total_instructions, pcore_execution_energy, pcore_cumulative_instructions = parse_execution_log(pcore_execution_file)
    mixed_execution_time, mixed_total_instructions, mixed_execution_energy, mixed_cumulative_instructions = parse_execution_log(mixed_execution_file)

    metrics['execution']['pcore_cumulative_instructions'] = pcore_cumulative_instructions
    metrics['execution']['pcore_total_instructions'] = pcore_total_instructions
    metrics['execution']['pcore_total_energy'] = pcore_execution_energy
    metrics['execution']['pcore_total_time'] = pcore_execution_time

    metrics['execution']['mixed_cumulative_instructions'] = mixed_cumulative_instructions
    metrics['execution']['mixed_total_instructions'] = mixed_total_instructions
    metrics['execution']['mixed_total_energy'] = mixed_execution_energy
    metrics['execution']['mixed_total_time'] = mixed_execution_time

    # Parse the logs for each governor
    for governor in governors:
        governor_periodic_file = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{governor}/periodic_counters.log"))
        governor_execution_file = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{governor}/execution.log"))

        if governor_periodic_file:
            gov_periodic_instructions, gov_periodic_energy, gov_periodic_time = parse_periodic_log(governor_periodic_file[0])
            metrics['periodic']['governors'][governor] = {
                'instructions': gov_periodic_instructions,
                'energy': gov_periodic_energy,
                'time': gov_periodic_time
            }

        if governor_execution_file:
            gov_execution_time, gov_total_instructions, gov_execution_energy, gov_cumulative_instructions = parse_execution_log(governor_execution_file[0])
            metrics['execution']['governors'][governor] = {
                'cumulative_instructions': gov_cumulative_instructions,
                'total_instructions': gov_total_instructions,
                'energy': gov_execution_energy,
                'time': gov_execution_time
            }

    return metrics


# Function to plot EDP for all run types
def plot_edp(applications, edps, frequency, output_dir):
    plt.figure(figsize=(12, 6))
    bar_width = 0.1
    index = np.arange(len(applications))
    
    labels = ['P-core max', 'Mixed', "performance","ondemand","conservative","schedutil","powersave"]
    colors = ['blue', 'green', 'red', 'orange', 'purple', 'brown', 'black']

    for i, label in enumerate(labels):
        plt.bar(index + i * bar_width, [app[i] for app in edps], bar_width, label=label, color=colors[i], alpha=0.7)
    
    plt.xlabel('Applications')
    plt.ylabel('EDP (J·s)')
    plt.title(f'EDP Comparison')
    plt.xticks(index + 3 * bar_width, applications, rotation=45, ha="right")
    plt.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"edp_comparison.png"))
    plt.close()

# Main function to retrieve, compute EDP, and plot results
def main():
    applications = config.parsec_apps
    frequency = "3500MHz"
    governors = ["performance","ondemand","conservative","schedutil","powersave"]
    
    output_dir = os.path.join(config.ROOTPATH, f"{config.EVALUATION_FOLDER}/plots/bars")
    os.makedirs(output_dir, exist_ok=True)
    
    edps = []
    
    for application_name in applications:
        metrics = gather_metrics(application_name, frequency, governors)
        if metrics is None:
            print(f"Metrics not found for {application_name} at {frequency}")
            continue

        # Calculate EDP for P-core and Mixed-core (using execution log data)
        pcore_edp = compute_edp(metrics['periodic']['pcore_energy'], metrics['periodic']['pcore_time'])
        mixed_edp = compute_edp(metrics['periodic']['mixed_energy'], metrics['periodic']['mixed_time'])

        app_edps = [pcore_edp, mixed_edp]

        # Calculate EDP for each governor
        for governor in governors:
            governor_energy = metrics['periodic']['governors'][governor]['energy']
            governor_time = metrics['periodic']['governors'][governor]['time']
            governor_edp = compute_edp(governor_energy, governor_time)
            app_edps.append(governor_edp)
        
        edps.append(app_edps)

    # Plot the EDP results
    plot_edp(applications, edps, frequency, output_dir)

if __name__ == "__main__":
    main()
