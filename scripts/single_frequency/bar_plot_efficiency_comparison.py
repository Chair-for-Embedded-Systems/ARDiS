"""
    A script to generate bar plots comparing the energy efficiency of E-core and P-core for each application at different frequencies.
"""

import os
import re
import glob
import sys
import numpy as np
import matplotlib.pyplot as plt

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

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

            # Check for SYSTEM entries and accumulate energy (for energy-pkg)
            energy_match = re.search(r'power/energy-psys/ = (\d+\.\d+)', line)
            if energy_match:
                energy = float(energy_match.group(1))
                all_energies.append(energy)
                total_energy += energy
    all_efficiencies = [((instructions / energy) * 1e-6) for instructions, energy in zip(all_instructions, all_energies)]
    return total_instructions, total_energy, np.mean(all_energies), np.mean(all_efficiencies)

# Function to gather metrics for each application at a given frequency and energy type
def gather_metrics(application_name, frequency):
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
    _, _, _, e_mean_effiency = parse_periodic_log(ecore_file)
    _, _, _, p_mean_effiency = parse_periodic_log(pcore_file)

    return {
        'ecore_efficiency': e_mean_effiency,
        'pcore_efficiency': p_mean_effiency
    }

# Function to generate a plot for each application with efficiency across frequencies
def plot_application_efficiency(application_name, frequencies, ecore_efficiencies, pcore_efficiencies, output_dir):
    plt.figure(figsize=(10, 6))
    bar_width = 0.35
    index = np.arange(len(frequencies))

    # Create the bars for E-core and P-core efficiency
    bars1 = plt.bar(index, ecore_efficiencies, bar_width, label='E-core', color='red', alpha=0.7)
    bars2 = plt.bar(index + bar_width, pcore_efficiencies, bar_width, label='P-core', color='blue', alpha=0.7)

    plt.xlabel('Frequencies')
    plt.ylabel('Energy Efficiency')
    plt.title(f'Energy Efficiency of {application_name}')
    plt.xticks(index + bar_width / 2, frequencies, rotation=45, ha="right")
    plt.legend()

    plt.tight_layout()
    output_file = os.path.join(output_dir, f"{application_name}_efficiency.png")
    plt.savefig(output_file)
    plt.close()

# Main function to create all plots
def main():
    frequencies = [
        "1500MHz",
        "2000MHz",
        "2500MHz",
        "3000MHz",
        "3500MHz"
    ]
    
    output_dir = os.path.join(config.ROOTPATH, f"{config.PAPERPLOT_FOLDER}/bars")
    os.makedirs(output_dir, exist_ok=True)

    for application_name in config.parsec_apps:
        ecore_efficiencies = []
        pcore_efficiencies = []

        for frequency in frequencies:
            print(f"Processing {application_name} at {frequency}")
            metrics = gather_metrics(application_name, frequency)
            if metrics is None:
                continue

            # Gather efficiency data
            ecore_efficiencies.append(metrics['ecore_efficiency'])
            pcore_efficiencies.append(metrics['pcore_efficiency'])

        if ecore_efficiencies and pcore_efficiencies:
            plot_application_efficiency(application_name, frequencies, ecore_efficiencies, pcore_efficiencies, output_dir)

if __name__ == "__main__":
    main()
