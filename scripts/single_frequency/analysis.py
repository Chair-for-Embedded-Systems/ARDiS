import os
import re
import matplotlib.pyplot as plt
import glob
import sys

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

# Function to parse log file and get periodic instructions
def parse_periodic_instructions(log_file):
    time_points = []
    periodic_instructions = []

    with open(log_file, 'r') as file:
        for line in file:
            match = re.search(r'\[(\d+\.\d+)s\].*instructions = (\d+)', line)
            if match:
                time = float(match.group(1))
                instructions = int(match.group(2))
                
                time_points.append(time)
                periodic_instructions.append(instructions)
    
    return time_points, periodic_instructions

# Function to parse log file and get periodic energy for a given energy type
def parse_periodic_energy(log_file, energy_type):
    time_points = []
    periodic_energy = []

    with open(log_file, 'r') as file:
        for line in file:
            match = re.search(fr'\[(\d+\.\d+)s\].*power/energy-{energy_type}/ = (\d+)', line)
            if match:
                time = float(match.group(1))
                energy = int(match.group(2))
                
                time_points.append(time)
                periodic_energy.append(energy)
    
    return time_points, periodic_energy

# Function to plot periodic instructions for each application
def plot_instructions(application_name, pcore_file, ecore_file, output_directory):
    # Parse the logs to get time points and periodic instructions
    pcore_time, pcore_periodic_instr = parse_periodic_instructions(pcore_file)
    ecore_time, ecore_periodic_instr = parse_periodic_instructions(ecore_file)

    # Create a plot
    plt.figure(figsize=(10, 6))
    
    # Plot periodic instructions for P-core and E-core
    plt.plot(pcore_time, pcore_periodic_instr, label='P-core', color='blue', alpha=0.7)
    plt.plot(ecore_time, ecore_periodic_instr, label='E-core', color='red', alpha=0.7)

    # Add labels, title, legend, and grid
    plt.xlabel("Time (s)")
    plt.ylabel("Periodic Instructions")
    plt.title(f"{application_name} - Periodic Instructions Over Time")
    plt.legend()
    plt.grid(True)
    
    # Save the plot
    plt.tight_layout()
    plt.savefig(os.path.join(output_directory, f"{application_name}_periodic_instructions.png"))
    plt.close()

# Function to plot energy comparison for each application and energy type
def plot_energy_comparison(application_name, pcore_file, ecore_file, energy_type, output_directory):
    # Parse the logs to get time points and periodic energy for each type
    ecore_time, ecore_energy = parse_periodic_energy(ecore_file, energy_type)
    pcore_time, pcore_energy = parse_periodic_energy(pcore_file, energy_type)

    # Create a plot
    plt.figure(figsize=(10, 6))
    
    # Plot periodic energy for P-core and E-core
    plt.plot(pcore_time, pcore_energy, label='P-core', color='blue', alpha=0.7)
    plt.plot(ecore_time, ecore_energy, label='E-core', color='red', alpha=0.7)

    # Add labels, title, legend, and grid
    plt.xlabel("Time (s)")
    plt.ylabel(f"Periodic Energy ({energy_type}) (J)")
    plt.title(f"{application_name} - Periodic Energy ({energy_type}) Over Time")
    plt.legend()
    plt.grid(True)
    
    # Save the plot
    plt.tight_layout()
    plt.savefig(os.path.join(output_directory, f"{application_name}_periodic_energy_{energy_type}.png"))
    plt.close()

# Main script to process all applications
def main():
    # Ensure the output directory exists
    output_directory_instr = os.path.join(config.ROOTPATH, "plots/periodic/instructions")
    output_directory_energy = os.path.join(config.ROOTPATH, "plots/periodic/energy")
    os.makedirs(output_directory_instr, exist_ok=True)
    os.makedirs(output_directory_energy, exist_ok=True)

    log_directory = config.RESULTS_FOLDER

    frequency = "2000MHz"

    for application_name in config.available_apps:
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

        # Generate the instructions plot
        plot_instructions(application_name, pcore_file, ecore_file, output_directory_instr)

        # Generate energy comparison plots for each energy type
        for energy_type in ["cores", "pkg", "psys"]:
            plot_energy_comparison(application_name, pcore_file, ecore_file, energy_type, output_directory_energy)

if __name__ == "__main__":
    main()
