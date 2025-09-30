import os
import re
import sys
import matplotlib.pyplot as plt

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import ardis.config as config

# Function to parse the log file and extract execution time and energy
def parse_result_file(file_path, target_application="omnetpp"):
    execution_time = None
    energy_consumed = None

    with open(file_path, 'r') as file:
        for line in file:
            # Look for the target application's execution time
            #if f"{target_application} finished execution" in line:
            # Example: [Core 16]: spec-omnetpp's execution time = 732.42s
            match = re.search(rf"{target_application}'s execution time = ([\d.]+)s", line)
            if match:
                execution_time = float(match.group(1))

            # Look for total energy consumption (system-wide)
            if "Total energy consumed" in line:
                # Example: Total energy consumed (perf)= 58760.98 Joules
                match = re.search(r"Total energy consumed.*= ([\d.]+) Joules", line)
                if match:
                    energy_consumed = float(match.group(1))

    return execution_time, energy_consumed
# Function to extract data from the folder and classify them by core type and number of background applications
def collect_data(result_folder, target_application="omnetpp", frequency="3200MHz"):
    ecore_data = []
    pcore_data = []

    # Iterate over directories in the result folder (each experiment folder)
    for dir_name in os.listdir(result_folder):
        dir_path = os.path.join(result_folder, dir_name)
        
        # Ensure we are looking at directories and not files
        if not os.path.isdir(dir_path):
            continue

        # Only process directories matching the specified frequency
        if frequency not in dir_name:
            continue

        # Path to the execution log inside the experiment directory
        log_file_path = os.path.join(dir_path, "execution.log")
        if not os.path.exists(log_file_path):
            print(f"Missing execution.log in {dir_name}, skipping.")
            continue

        # Check if the directory corresponds to E core experiment
        if "motivECores" in dir_name:
            # Extract the number of background applications from the directory name
            match = re.search(rf"_motivECores_{frequency}_(\d+)", dir_name)
            if match:
                bg_apps = int(match.group(1))
                execution_time, energy_consumed = parse_result_file(log_file_path, target_application)
                ecore_data.append((bg_apps, execution_time, energy_consumed))

        # Check if the directory corresponds to P core experiment
        elif "motivPCores" in dir_name:
            # Extract the number of background applications from the directory name
            match = re.search(rf"_motivPCores_{frequency}_(\d+)", dir_name)
            if match:
                bg_apps = int(match.group(1))
                execution_time, energy_consumed = parse_result_file(log_file_path, target_application)
                pcore_data.append((bg_apps, execution_time, energy_consumed))

    # Sort the data by the number of background applications
    ecore_data.sort(key=lambda x: x[0])
    pcore_data.sort(key=lambda x: x[0])

    return ecore_data, pcore_data

# Function to plot execution time and energy
def plot_execution_time_and_energy(ecore_data, pcore_data, target_frequency, target_application, output_dir="output"):
    # Unpacking data for plotting
    ecore_bg_apps = [item[0] for item in ecore_data]
    ecore_exec_times = [item[1] for item in ecore_data]
    ecore_energy = [item[2] for item in ecore_data]

    pcore_bg_apps = [item[0] for item in pcore_data]
    pcore_exec_times = [item[1] for item in pcore_data]
    pcore_energy = [item[2] for item in pcore_data]

    # Plot execution time
    plt.figure(figsize=(10, 6))
    plt.plot(ecore_bg_apps, ecore_exec_times, marker='o', label="E Core Execution Time")
    plt.plot(pcore_bg_apps, pcore_exec_times, marker='o', label="P Core Execution Time")
    plt.xlabel("Number of Background Applications")
    plt.ylabel("Execution Time (s)")
    plt.title("Execution Time of omnetpp with Varying Background Applications")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, f"motivational_{target_application}_{target_frequency}_performance.png"))

    # Plot energy consumption (since energy is system-wide, both should have the same values)
    plt.figure(figsize=(10, 6))
    plt.plot(ecore_bg_apps, ecore_energy, marker='o', label="E Core Energy Consumption")
    plt.plot(pcore_bg_apps, pcore_energy, marker='o', label="P Core Energy Consumption")
    plt.xlabel("Number of Background Applications")
    plt.ylabel("Energy Consumption (J)")
    plt.title("Energy Consumption of omnetpp with Varying Background Applications")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, f"motivational_{target_application}_{target_frequency}_energy.png"))

# Main function to drive the analysis
def main():
    target_application="omnetpp"
    target_frequency="3200MHz"
    # Define the folder containing the result files
    result_folder = config.MOTIVATIONAL_RESULTS_FOLDER

    # Collect data from the result folder
    ecore_data, pcore_data = collect_data(result_folder, target_application, target_frequency)
    print(f"E Core Data: {ecore_data}")

    # Plot execution time and energy
    plot_execution_time_and_energy(ecore_data, pcore_data, target_frequency, target_application, config.PLOTS_FOLDER)

if __name__ == "__main__":
    main()
