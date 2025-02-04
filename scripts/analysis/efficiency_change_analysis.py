import os
import re
import sys
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import matplotlib.cm as cm

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

SHIFT_RANGE = 5  # Set the range up to which we look ahead for percentage changes

# Enable LaTeX rendering in Matplotlib (if needed)
plt.rcParams.update({
    "text.usetex": True,
    "font.family": "serif",
    "font.serif": ["Times"],
    "axes.labelsize": 12,
    "xtick.labelsize": 10,
    "ytick.labelsize": 10,
    "legend.fontsize": 10,
    "axes.titlesize": 12
})

# Define function to parse log file and plot efficiency
def parse_log_file_and_plot_efficiency(log_file_path, application_name, frequency, ax1):
    # Define regex patterns to match instruction and energy data
    instruction_pattern = r"\[(\d+\.\d+)s\] PID \d+: instructions = (\d+)"
    energy_pattern = r"\[(\d+\.\d+)s\] SYSTEM: power/energy-pkg/ = ([\d\.]+) \| power/energy-cores/ = ([\d\.]+) \| power/energy-psys/ = ([\d\.]+)"

    # Initialize lists to store parsed data
    timestamps = []
    instructions = []
    energy_psys = []

    # Parse the log file to extract instructions and energy data
    with open(log_file_path, 'r') as file:
        for line in file:
            # Match instruction lines
            instruction_match = re.match(instruction_pattern, line)
            if instruction_match:
                timestamps.append(float(instruction_match.group(1)))
                instructions.append(int(instruction_match.group(2)))

            # Match energy_psys lines and ensure they follow an instruction line
            energy_match = re.match(energy_pattern, line)
            if energy_match:
                if timestamps and len(timestamps) == len(instructions):  # Ensure corresponding instruction entry
                    energy_psys.append(float(energy_match.group(4)))
                else:
                    print("Warning: Mismatched energy and instruction entries.")

    # Check if lists are balanced
    if len(timestamps) != len(instructions) or len(instructions) != len(energy_psys):
        print(f"Error: Mismatch between instruction and energy data counts in the log file. {len(timestamps)} timestamps, {len(instructions)} instructions, {len(energy_psys)} energy values.")
        return

    # Create a DataFrame with the parsed data
    df = pd.DataFrame({
        "timestamp": timestamps,
        "instructions": instructions,
        "energy_psys": energy_psys
    })

    # Calculate Efficiency (Instructions per Energy Unit)
    df["efficiency"] = df["instructions"] / df["energy_psys"]

    # Calculate percentage change in efficiency for the next 1 to SHIFT_RANGE epochs
    for shift in range(1, SHIFT_RANGE):
        df[f"efficiency_percent_change_next_{shift}"] = (df["efficiency"].shift(-shift) - df["efficiency"]) / df["efficiency"] * 100

    # Calculate min and max percentage change across the next epochs
    df["min_efficiency_percent_change"] = df[[f"efficiency_percent_change_next_{shift}" for shift in range(1, SHIFT_RANGE)]].min(axis=1)
    df["max_efficiency_percent_change"] = df[[f"efficiency_percent_change_next_{shift}" for shift in range(1, SHIFT_RANGE)]].max(axis=1)

    # Plotting
    #fig, ax1 = plt.subplots(figsize=(14, 8))

    # Plot efficiency over time on the primary y-axis
    ax1.plot(df["timestamp"], df["efficiency"], label="Efficiency (IPJ)", color="steelblue")
    ax1.set_xlabel("Timestamp (s)")
    ax1.set_ylabel("Efficiency (Instructions/Energy)")
    #ax1.tick_params(axis='y', labelcolor="steelblue")
    ax1.set_title(application_name)

    # Create a secondary y-axis for percentage changes in future efficiency values
    ax2 = ax1.twinx()

    # Use a vivid color palette for the percentage change lines
    colors = cm.get_cmap("tab20c", SHIFT_RANGE).colors
    for i, color in enumerate(colors[:SHIFT_RANGE-1], start=1):
        ax2.plot(df["timestamp"], df[f"efficiency_percent_change_next_{i}"], 
                 label=f"Efficiency \% Change in Next {i} Epoch(s)", color=color, linestyle="--", alpha=0.8)

    # Shade the area between the minimum and maximum percentage change lines
    ax2.fill_between(df["timestamp"], df["min_efficiency_percent_change"], df["max_efficiency_percent_change"], 
                     color="lightcoral", alpha=0.3, label="Range of \% Changes")

    ax2.set_ylabel("Efficiency \% Change for Future Epochs")
    #ax2.tick_params(axis='y')

    # Show grid and legend
    #fig.tight_layout()
    ax1.grid(True, linestyle="--", alpha=0.9)
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")
    
    # Save the plot to the specified directory
    #plt.savefig(os.path.join(config.PLOTS_FOLDER, f"delta_efficiency_analysis_{application_name}_{frequency}.png"))

# Update the main function to process and plot efficiency data
def process_experiment_results_efficiency_plots(results_folder, application_name, frequency, core_type):
    for experiment_folder in os.listdir(results_folder):
        if application_name in experiment_folder and frequency in experiment_folder and core_type in experiment_folder:
            log_path = os.path.join(results_folder, experiment_folder, 'periodic_counters.log')
            if os.path.isfile(log_path):
                parse_log_file_and_plot_efficiency(log_path, application_name, frequency)

# Main function to create the figure with subplots
def plot_multiple_applications(result_folder, application_names, frequency, core_type):
    fig, axs = plt.subplots(2, 2, figsize=(12, 8))  # 2x2 grid for 4 applications

    for i, application_name in enumerate(application_names):
        row, col = divmod(i, 2)  # Determine subplot position
        ax1 = axs[row, col]  # Primary y-axis for periodic IPC
        
        # Find the log file path for the application and plot data
        for experiment_folder in os.listdir(result_folder):
            if application_name in experiment_folder and frequency in experiment_folder and core_type in experiment_folder:
                print(f"Processing {application_name} in {experiment_folder}")
                log_path = os.path.join(result_folder, experiment_folder, 'periodic_counters.log')
                if os.path.isfile(log_path):
                    parse_log_file_and_plot_efficiency(log_path, application_name, frequency, ax1)
    
    # Configure layout and save the figure
    plt.tight_layout()
    plt.savefig(os.path.join(config.PLOTS_FOLDER, f"delta_energy_analysis_grouped_{frequency}.pdf"))
    plt.show()

def main():

    
    result_folder = config.SINGLE_RESULTS_FOLDER
    frequency = "3200MHz"
    core_type = "Pcore"
    application_names = ["parsec-splash2x.radix", "parsec-dedup", "parsec-splash2x.lu_ncb", "parsec-splash2x.ocean_ncp"]  # Replace with your selected application names
    plot_multiple_applications(result_folder, application_names, frequency, core_type)

    '''
    result_folder = config.SINGLE_RESULTS_FOLDER
    frequency = "3200MHz"
    core_type = "Pcore"
    application_names = ["parsec-splash2x.radix", "parsec-dedup", "parsec-splash2x.lu_ncb", "parsec-splash2x.ocean_ncp"]
    for application_name in config.parsec_apps:
        process_experiment_results_efficiency_plots(result_folder, application_name, frequency, core_type)
    '''

if __name__ == "__main__":
    main()
