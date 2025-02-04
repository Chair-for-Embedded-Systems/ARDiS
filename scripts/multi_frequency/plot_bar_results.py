import os
import re
import glob
import sys
import numpy as np
import matplotlib.pyplot as plt

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

# Function to parse execution log and retrieve instructions, energy, and time
def parse_execution_log(log_file):
    total_time = None
    total_energy = None
    total_instructions = None

    with open(log_file, 'r') as file:
        for line in file:
            if "Total time elapsed (perf)=" in line:
                total_time = float(re.search(r'Total time elapsed \(perf\)= (\d+\.\d+)', line).group(1))
            if "Total instructions executed =" in line:
                total_instructions = int(re.search(r'Total instructions executed = (\d+)', line).group(1))
            if "Total energy consumed (perf)=" in line:
                total_energy = float(re.search(r'Total energy consumed \(perf\)= (\d+\.\d+)', line).group(1))
    
    return total_time, total_instructions, total_energy

# Function to gather metrics for P-core and Mixed-core results
def gather_metrics(application_name, frequency):
    pcore_dirs = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{frequency}_Pcore"))
    mixed_dirs = glob.glob(os.path.join(config.PARSEC_MIXED_STATIC_FOLDERS[0], f"*_{application_name}_Mixed*"))

    if not (pcore_dirs and mixed_dirs):
        return None

    # Assume the execution log file is named "execution.log"
    pcore_file = os.path.join(pcore_dirs[0], "execution.log")
    mixed_file = os.path.join(mixed_dirs[0], "execution.log")

    pcore_time, pcore_instr, pcore_energy = parse_execution_log(pcore_file)
    mixed_time, mixed_instr, mixed_energy = parse_execution_log(mixed_file)
    
    return {
        'pcore_time': pcore_time,
        'pcore_instructions': pcore_instr,
        'pcore_energy': pcore_energy,
        'mixed_time': mixed_time,
        'mixed_instructions': mixed_instr,
        'mixed_energy': mixed_energy
    }

# Function to compute baseline efficiency for governor
def compute_baseline_efficiency(application_name, governor, baseline_directory):
    log_file = glob.glob(os.path.join(baseline_directory, f"*_{application_name}_{governor}/execution.log"))
    if not log_file:
        return np.nan, np.nan, np.nan  # Return NaN if the log file is not found

    total_time, total_instructions, total_energy = parse_execution_log(log_file[0])
    if total_time is None or total_energy is None:
        print(f"Error parsing log file for {application_name} with {governor}")
        return np.nan, np.nan, np.nan

    energy_efficiency = (total_instructions / total_energy) * 1e-6 if total_energy > 0 else np.nan
    return energy_efficiency, total_time, total_energy

# Plot execution time for all run types
def plot_execution_time(applications, times, frequency, output_dir):
    plt.figure(figsize=(12, 6))
    bar_width = 0.1
    index = np.arange(len(applications))
    
    labels = [
        'P-core max', 
        'Mixed', 
        'Performance', 
        #'Powersave', 
        'Ondemand', 
        'Conservative', 
        'Schedutil'
        ]
    colors = ['blue', 'green', 'red', 'orange', 'purple', 'brown', 'cyan']
    
    for i, label in enumerate(labels):
        normalized_times = [app[i] / app[0] for app in times]  # Normalize to P-core max
        plt.bar(index + i * bar_width, normalized_times, bar_width, label=label, color=colors[i], alpha=0.7)
    
    plt.xlabel('Applications')
    plt.ylabel('Execution Time (s)')
    plt.ylim(0.4)
    plt.title(f'Execution Time Comparison at {frequency}')
    plt.xticks(index + 3 * bar_width, applications, rotation=45, ha="right")
    plt.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"governors_execution_time_comparison_{frequency}.png"))
    plt.close()

# Plot energy efficiency for all run types
def plot_energy_efficiency(applications, efficiencies, frequency, output_dir):
    plt.figure(figsize=(12, 6))
    bar_width = 0.1
    index = np.arange(len(applications))
    
    labels = [
        'P-core max', 
        'Mixed', 
        'Performance', 
        #'Powersave', 
        'Ondemand', 
        'Conservative', 
        'Schedutil'
        ]
    colors = ['blue', 'green', 'red', 'orange', 'purple', 'brown', 'cyan']
    
    for i, label in enumerate(labels):
        normalized_efficiencies = [app[i] / app[0] for app in efficiencies]  # Normalize to P-core max
        plt.bar(index + i * bar_width, normalized_efficiencies, bar_width, label=label, color=colors[i], alpha=0.7)
    
    plt.xlabel('Applications')
    plt.ylabel('Energy Efficiency (MI/J)')
    plt.title(f'Energy Efficiency Comparison at {frequency}')
    plt.xticks(index + 3 * bar_width, applications, rotation=45, ha="right")
    plt.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"governors_energy_efficiency_comparison_{frequency}.png"))
    plt.close()


# Plot energy efficiency for all run types
def plot_energy(applications, energies, frequency, output_dir):
    plt.figure(figsize=(12, 6))
    bar_width = 0.1
    index = np.arange(len(applications))
    
    labels = [
        'P-core max', 
        'Mixed', 
        'Performance', 
        #'Powersave', 
        'Ondemand', 
        'Conservative', 
        'Schedutil'
        ]
    colors = ['blue', 'green', 'red', 'orange', 'purple', 'brown', 'cyan']
    
    for i, label in enumerate(labels):
        normalized_energies = [app[i] / app[0] for app in energies]  # Normalize to P-core max
        plt.bar(index + i * bar_width, normalized_energies, bar_width, label=label, color=colors[i], alpha=0.7)
    
    plt.xlabel('Applications')
    plt.ylabel('Energy (J)')
    plt.title(f'Energy Comparison at {frequency}')
    plt.xticks(index + 3 * bar_width, applications, rotation=45, ha="right")
    plt.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"governors_energy_comparison_{frequency}.png"))
    plt.close()

# Main function to process and plot results
def main():
    applications = config.parsec_apps
    frequency = "3500MHz"
    governors = [
        "performance", 
        #"powersave", 
        "ondemand", 
        "conservative", 
        "schedutil"
        ]
    
    baseline_directory = config.PARSEC_GOVERNOR_FOLDER
    output_dir = os.path.join(config.ROOTPATH, f"{config.EVALUATION_FOLDER}/plots/bars")
    os.makedirs(output_dir, exist_ok=True)
    
    times = []
    efficiencies = []
    energies = []

    for application_name in applications:
        # Step 1: Gather metrics for P-core max and Mixed core
        pcore_metrics = gather_metrics(application_name, frequency)
        print(f"Processing {application_name} at {frequency}")
        print(pcore_metrics)
        if not pcore_metrics:
            print(f"Metrics not found for {application_name} at {frequency}")
            continue

        total_instructions = pcore_metrics['mixed_instructions']
        
        # Step 2: Gather execution time and efficiency for baseline governors
        app_times = [pcore_metrics['pcore_time'], pcore_metrics['mixed_time']]
        app_efficiencies = [
            pcore_metrics['pcore_instructions'] / pcore_metrics['pcore_energy'] * 1e-6,
            pcore_metrics['mixed_instructions'] / pcore_metrics['mixed_energy'] * 1e-6
        ]
        app_energies = [pcore_metrics['pcore_energy'], pcore_metrics['mixed_energy']]

        for governor in governors:
            efficiency, exec_time, energy = compute_baseline_efficiency(application_name, governor, baseline_directory)
            app_times.append(exec_time)
            app_efficiencies.append(efficiency)
            app_energies.append(energy)
        
        print(app_times)
        times.append(app_times)
        efficiencies.append(app_efficiencies)
        energies.append(app_energies)

    # Step 3: Plot execution times and energy efficiency
    #plot_execution_time(applications, times, frequency, output_dir)
    #plot_energy_efficiency(applications, efficiencies, frequency, output_dir)
    plot_energy(applications, energies, frequency, output_dir)

if __name__ == "__main__":
    main()