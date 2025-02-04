import os 
import re
import sys
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.cm as cm

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config

SHIFT_RANGE = 5  # Set the range up to which we look ahead for percentage changes

# Enable LaTeX rendering in Matplotlib (if needed)
plt.rcParams.update({
    "text.usetex": True,  # Use LaTeX to render text
    "font.family": "serif",  # Use serif fonts
    "font.serif": ["Times"],  # Use Times font for the plot
    "axes.labelsize": 12,  # Font size for axis labels
    "xtick.labelsize": 10,  # Font size for x-axis tick labels
    "ytick.labelsize": 10,  # Font size for y-axis tick labels
    "legend.fontsize": 10,  # Font size for the legend
    "axes.titlesize": 12  # Font size for the title
})

# File path to the log file
def parse_log_file_and_plot_singles(log_file_path, application_name, frequency):
    # Define regex patterns to match PID data and extract fields
    pid_pattern = r"\[(\d+\.\d+)s\] PID \d+: instructions = (\d+) \| LLC-loads = (\d+) \| LLC-load-misses = (\d+) \| LLC-stores = (\d+) \| LLC-store-misses = (\d+) \| cycles = (\d+) \| branch-misses = (\d+) \| branches = (\d+)"

    # Initialize lists to store parsed data
    timestamps = []
    instructions = []
    cycles = []

    # Parse the log file to extract PID data
    with open(log_file_path, 'r') as file:
        for line in file:
            pid_match = re.match(pid_pattern, line)
            if pid_match:
                # Extract timestamp, instructions, and cycles
                timestamps.append(float(pid_match.group(1)))
                instructions.append(int(pid_match.group(2)))
                cycles.append(int(pid_match.group(7)))

    # Create a DataFrame with the parsed data
    df = pd.DataFrame({
        "timestamp": timestamps,
        "instructions": instructions,
        "cycles": cycles
    })

    # Calculate IPC (Instructions Per Cycle)
    df["ipc"] = df["instructions"] / df["cycles"]

    # Calculate percentage change in IPC for the next 1 to SHIFT_RANGE epochs
    for shift in range(1, SHIFT_RANGE):
        df[f"ipc_percent_change_next_{shift}"] = (df["ipc"].shift(-shift) - df["ipc"]) / df["ipc"] * 100

    # Calculate min and max percentage change across the next epochs
    df["min_ipc_percent_change"] = df[[f"ipc_percent_change_next_{shift}" for shift in range(1, SHIFT_RANGE)]].min(axis=1)
    df["max_ipc_percent_change"] = df[[f"ipc_percent_change_next_{shift}" for shift in range(1, SHIFT_RANGE)]].max(axis=1)

    # Plotting
    fig, ax1 = plt.subplots(figsize=(14, 8))

    # Plot periodic IPC over time on the primary y-axis
    ax1.plot(df["timestamp"], df["ipc"], label="Periodic IPC", color="steelblue")
    ax1.set_xlabel("Timestamp (s)")
    ax1.set_ylabel("IPC", color="steelblue")
    ax1.tick_params(axis='y', labelcolor="steelblue")
    ax1.set_title("IPC Over Time with Future IPC Percentage Changes for Next Epochs")

    # Create a secondary y-axis for percentage changes in future IPC values
    ax2 = ax1.twinx()

    # Use a more vivid color palette for the percentage change lines
    colors = cm.get_cmap("tab20c", SHIFT_RANGE).colors  # Tab10 colormap with vivid colors
    for i, color in enumerate(colors[:SHIFT_RANGE-1], start=1):
        ax2.plot(df["timestamp"], df[f"ipc_percent_change_next_{i}"], 
                 label=f"IPC \% Change in Next {i} Epoch(s)", color=color, linestyle="--", alpha=0.8)

    # Shade the area between the minimum and maximum percentage change lines
    ax2.fill_between(df["timestamp"], df["min_ipc_percent_change"], df["max_ipc_percent_change"], 
                     color="lightcoral", alpha=0.3, label="Range of \% Changes")

    ax2.set_ylabel("IPC \% Change for Future Epochs", color="darkred")
    ax2.tick_params(axis='y', labelcolor="darkred")

    # Show grid and legend
    fig.tight_layout()  # Adjust layout to prevent overlap
    ax1.grid(True, linestyle="--", alpha=0.9)
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")
    
    # Save the plot to the specified directory
    plt.savefig(os.path.join(config.PLOTS_FOLDER, f"delta_ipc_analysis_{application_name}_{frequency}.png"))

# Main function to process all log files and compile dataset
def process_experiment_results_single_plots(results_folder, application_name, frequency, core_type):
    for experiment_folder in os.listdir(results_folder):
        if application_name in experiment_folder and frequency in experiment_folder and core_type in experiment_folder:
            log_path = os.path.join(results_folder, experiment_folder, 'periodic_counters.log')
            if os.path.isfile(log_path):
                parse_log_file_and_plot_singles(log_path, application_name, frequency)



# Function to parse the log file and plot within a subplot
def parse_log_file_and_plot(log_file_path, application_name, frequency, ax1):
    # Define regex patterns to match PID data and extract fields
    pid_pattern = r"\[(\d+\.\d+)s\] PID \d+: instructions = (\d+) \| LLC-loads = (\d+) \| LLC-load-misses = (\d+) \| LLC-stores = (\d+) \| LLC-store-misses = (\d+) \| cycles = (\d+) \| branch-misses = (\d+) \| branches = (\d+)"

    # Initialize lists to store parsed data
    timestamps = []
    instructions = []
    cycles = []

    # Parse the log file to extract PID data
    with open(log_file_path, 'r') as file:
        for line in file:
            pid_match = re.match(pid_pattern, line)
            if pid_match:
                # Extract timestamp, instructions, and cycles
                timestamps.append(float(pid_match.group(1)))
                instructions.append(int(pid_match.group(2)))
                cycles.append(int(pid_match.group(7)))

    # Create a DataFrame with the parsed data
    df = pd.DataFrame({
        "timestamp": timestamps,
        "instructions": instructions,
        "cycles": cycles
    })

    # Calculate IPC (Instructions Per Cycle)
    df["ipc"] = df["instructions"] / df["cycles"]

    # Calculate percentage change in IPC for the next 1 to SHIFT_RANGE epochs
    for shift in range(1, SHIFT_RANGE):
        df[f"ipc_percent_change_next_{shift}"] = (df["ipc"].shift(-shift) - df["ipc"]) / df["ipc"] * 100

    # Calculate min and max percentage change across the next epochs
    df["min_ipc_percent_change"] = df[[f"ipc_percent_change_next_{shift}" for shift in range(1, SHIFT_RANGE)]].min(axis=1)
    df["max_ipc_percent_change"] = df[[f"ipc_percent_change_next_{shift}" for shift in range(1, SHIFT_RANGE)]].max(axis=1)

    # Plot periodic IPC over time on the primary y-axis (ax1) - only once
    ax1.plot(df["timestamp"], df["ipc"], label="Periodic IPC", color="#0B032D", linewidth=2)
    ax1.set_xlabel("Timestamp (s)")
    ax1.set_ylabel("IPC")
    ax1.set_ylim(0)  # Set x-axis limits to the maximum timestamp
    ax1.grid(True, linestyle="--", alpha=0.9)
    ax1.tick_params(axis='y')
    ax1.set_title(f"{application_name} IPC Over Time")

    # Plot percentage changes on a secondary y-axis (ax2) - do not replot the IPC line
    ax2 = ax1.twinx()
    colors = np.array(["#717568", "#9BC1BC", "#0A8754", "#d62728", "#9467bd"])  # Color palette for percentage changes
    for i, color in enumerate(colors[:SHIFT_RANGE-1], start=1):
        ax2.plot(df["timestamp"], df[f"ipc_percent_change_next_{i}"], 
                 label=f"IPC \% Change in Next {i} Epoch(s)", color=color, linewidth=0.5, alpha=0.8)

    # Shade the area between the min and max percentage change lines
    ax2.fill_between(df["timestamp"], df["min_ipc_percent_change"], df["max_ipc_percent_change"], 
                     color="#BFD7EA", alpha=0.5, label="Range of \% Changes")

    ax2.set_ylabel("IPC \% Change for Future Epochs")
    ax2.tick_params(axis='y')

    # Only add legends to the secondary y-axis items
    handles, labels = ax2.get_legend_handles_labels()
    ax2.legend(handles, labels, loc="upper right")

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
                    parse_log_file_and_plot(log_path, application_name, frequency, ax1)
    
    # Configure layout and save the figure
    plt.tight_layout()
    plt.savefig(os.path.join(config.PLOTS_FOLDER, f"delta_ipc_analysis_grouped_{frequency}.png"))
    plt.show()

# Main execution function
def main():
    result_folder = config.SINGLE_RESULTS_FOLDER
    frequency = "3200MHz"
    core_type = "Pcore"
    application_names = ["parsec-splash2x.radix", "parsec-dedup", "parsec-splash2x.lu_ncb", "parsec-splash2x.ocean_ncp"]  # Replace with your selected application names
    plot_multiple_applications(result_folder, application_names, frequency, core_type)
    #for application_name in config.parsec_apps:
    #    process_experiment_results_single_plots(result_folder, application_name, frequency, core_type)

if __name__ == "__main__":
    main()
