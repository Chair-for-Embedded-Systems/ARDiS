import os
import re
import sys
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import matplotlib.cm as cm

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import ardis.config as config

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

# File path to the log file
def parse_log_file_and_plot_energy(log_file_path, application_name, frequency):
    # Define regex patterns to match energy data and extract fields
    energy_pattern = r"\[(\d+\.\d+)s\] SYSTEM: power/energy-pkg/ = ([\d\.]+) \| power/energy-cores/ = ([\d\.]+) \| power/energy-psys/ = ([\d\.]+)"

    # Initialize lists to store parsed data
    timestamps = []
    energy_psys = []

    # Parse the log file to extract energy data
    with open(log_file_path, 'r') as file:
        for line in file:
            energy_match = re.match(energy_pattern, line)
            if energy_match:
                # Extract timestamp and energy values
                timestamps.append(float(energy_match.group(1)))
                energy_psys.append(float(energy_match.group(3)))

    # Create a DataFrame with the parsed data
    df = pd.DataFrame({
        "timestamp": timestamps,
        "energy_psys": energy_psys
    })

    # Calculate percentage change in energy_psys for the next 1 to SHIFT_RANGE epochs
    for shift in range(1, SHIFT_RANGE):
        df[f"energy_percent_change_next_{shift}"] = (df["energy_psys"].shift(-shift) - df["energy_psys"]) / df["energy_psys"] * 100

    # Calculate min and max percentage change across the next epochs
    df["min_energy_percent_change"] = df[[f"energy_percent_change_next_{shift}" for shift in range(1, SHIFT_RANGE)]].min(axis=1)
    df["max_energy_percent_change"] = df[[f"energy_percent_change_next_{shift}" for shift in range(1, SHIFT_RANGE)]].max(axis=1)

    # Plotting
    fig, ax1 = plt.subplots(figsize=(14, 8))

    # Plot periodic energy_psys over time on the primary y-axis
    ax1.plot(df["timestamp"], df["energy_psys"], label="Periodic Energy (Pkg)", color="steelblue")
    ax1.set_xlabel("Timestamp (s)")
    ax1.set_ylabel("Energy (Pkg)", color="steelblue")
    ax1.tick_params(axis='y', labelcolor="steelblue")
    ax1.set_title("Energy Over Time with Future Energy Percentage Changes for Next Epochs")

    # Create a secondary y-axis for percentage changes in future energy_psys values
    ax2 = ax1.twinx()

    # Use a more vivid color palette for the percentage change lines
    colors = cm.get_cmap("tab20c", SHIFT_RANGE).colors
    for i, color in enumerate(colors[:SHIFT_RANGE-1], start=1):
        ax2.plot(df["timestamp"], df[f"energy_percent_change_next_{i}"], 
                 label=f"Energy \% Change in Next {i} Epoch(s)", color=color, linestyle="--", alpha=0.8)

    # Shade the area between the minimum and maximum percentage change lines
    ax2.fill_between(df["timestamp"], df["min_energy_percent_change"], df["max_energy_percent_change"], 
                     color="lightcoral", alpha=0.3, label="Range of \% Changes")

    ax2.set_ylabel("Energy \% Change for Future Epochs", color="darkred")
    ax2.tick_params(axis='y', labelcolor="darkred")

    # Show grid and legend
    fig.tight_layout()
    ax1.grid(True, linestyle="--", alpha=0.9)
    ax1.legend(loc="upper left")
    ax2.legend(loc="upper right")
    
    # Save the plot to the specified directory
    plt.savefig(os.path.join(config.PLOTS_FOLDER, f"delta_energy_analysis_{application_name}_{frequency}.png"))

# Update the main function to process and plot energy data
def process_experiment_results_energy_plots(results_folder, application_name, frequency, core_type):
    for experiment_folder in os.listdir(results_folder):
        if application_name in experiment_folder and frequency in experiment_folder and core_type in experiment_folder:
            log_path = os.path.join(results_folder, experiment_folder, 'periodic_counters.log')
            if os.path.isfile(log_path):
                parse_log_file_and_plot_energy(log_path, application_name, frequency)

def main():
    result_folder = config.SINGLE_RESULTS_FOLDER
    frequency = "3200MHz"
    core_type = "Pcore"
    application_names = ["parsec-splash2x.radix", "parsec-dedup", "parsec-splash2x.lu_ncb", "parsec-splash2x.ocean_ncp"]
    for application_name in config.parsec_apps:
        process_experiment_results_energy_plots(result_folder, application_name, frequency, core_type)

if __name__ == "__main__":
    main()