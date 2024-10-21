import os
import re
import glob
import sys
import numpy as np
import matplotlib.pyplot as plt

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
import config

def parse_execution_log(log_file):
    last_cumulative_instructions = None
    
    with open(log_file, 'r') as file:
        for line in file:
            # Look for the cumulative instructions line and update the value
            cumulative_match = re.search(r'Cumulative Instructions = (\d+)', line)
            if cumulative_match:
                last_cumulative_instructions = int(cumulative_match.group(1))
    
    # Return the last cumulative instructions found
    return last_cumulative_instructions


# Function to compute variance
def compute_variance(data):
    # Filter out NaN values before computing variance
    filtered_data = [x for x in data if not np.isnan(x)]
    if len(filtered_data) > 1:
        return np.var(filtered_data)
    return np.nan

# Function to gather metrics for P-core, E-core, and all governors from execution logs
def gather_instruction_metrics(application_name, governors):
    # Paths for execution logs for P-core and E-core at all frequencies
    frequencies = ["3500MHz", "3000MHz", "2500MHz", "2000MHz", "1500MHz"]
    metrics = {
        'pcore_total_instructions': [],
        'ecore_total_instructions': [],
        'governors': {}
    }

    # Gather total instructions for P-core at each frequency
    for frequency in frequencies:
        pcore_dirs = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{frequency}_Pcore"))
        ecore_dirs = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{frequency}_Ecore"))

        if pcore_dirs:
            pcore_execution_file = os.path.join(pcore_dirs[0], "execution.log")
            pcore_total_instructions = parse_execution_log(pcore_execution_file)
            metrics['pcore_total_instructions'].append(pcore_total_instructions)
        else:
            metrics['pcore_total_instructions'].append(np.nan)

        if ecore_dirs:
            ecore_execution_file = os.path.join(ecore_dirs[0], "execution.log")
            ecore_total_instructions = parse_execution_log(ecore_execution_file)
            metrics['ecore_total_instructions'].append(ecore_total_instructions)
        else:
            metrics['ecore_total_instructions'].append(np.nan)

    # Gather total instructions for each governor
    for governor in governors:
        governor_execution_file = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{governor}/execution.log"))
        if governor_execution_file:
            governor_total_instructions = parse_execution_log(governor_execution_file[0])
            metrics['governors'][governor] = governor_total_instructions
        else:
            metrics['governors'][governor] = np.nan

    return metrics


# Function to plot total instructions for each execution type and governor, and add mean line
def plot_total_instructions(application_name, instruction_data, output_dir):
    plt.figure(figsize=(10, 6))
    bar_width = 0.6
    index = np.arange(15)  # 15 bars: 5 for P-core, 5 for E-core, 5 for governors

    # Labels for the bars
    labels = ['P-core F1', 'P-core F2', 'P-core F3', 'P-core F4', 'P-core F5',  # P-core frequencies
              'E-core F1', 'E-core F2', 'E-core F3', 'E-core F4', 'E-core F5',  # E-core frequencies
              'performance', 'powersave', 'ondemand', 'conservative', 'schedutil']  # Governors

    colors = ['blue'] * 5 + ['green'] * 5 + ['red', 'orange', 'purple', 'brown', 'black']

    # Plotting the total instructions as bars
    plt.bar(index, instruction_data, bar_width, color=colors, alpha=0.7)

    # Calculate and plot the mean
    mean_value = np.nanmean(instruction_data)
    plt.axhline(y=mean_value, color='red', linestyle='--', label=f'Mean: {mean_value:.0f}')

    # Add labels and title
    plt.title(f'Total Instructions Comparison for {application_name}')
    plt.xlabel('Execution Type and Governors')
    plt.ylabel('Total Instructions')
    plt.xticks(index, labels, rotation=45, ha="right")
    plt.legend()

    # Save the plot to a file
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{application_name}_instructions_comparison.png"))
    plt.close()


def parse_execution_log_for_cumulative_instrs(log_file):
    last_cumulative_instructions = None
    
    with open(log_file, 'r') as file:
        for line in file:
            # Look for the cumulative instructions line and update the value
            cumulative_match = re.search(r'Cumulative Instructions = (\d+)', line)
            if cumulative_match:
                last_cumulative_instructions = int(cumulative_match.group(1))
    
    # Return the last cumulative instructions found
    return last_cumulative_instructions


def get_mean_instructions(application_name):
    governors = ["performance", "powersave", "ondemand", "conservative", "schedutil"]
    # Gather instruction data for the application
    
    # Paths for execution logs for P-core and E-core at all frequencies
    frequencies = ["3500MHz", "3000MHz", "2500MHz", "2000MHz", "1500MHz"]
    metrics = {
        'pcore_total_instructions': [],
        'ecore_total_instructions': [],
        'governors': {}
    }

    # Gather total instructions for P-core at each frequency
    for frequency in frequencies:
        pcore_dirs = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{frequency}_Pcore"))
        ecore_dirs = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{frequency}_Ecore"))

        if pcore_dirs:
            pcore_execution_file = os.path.join(pcore_dirs[0], "execution.log")
            pcore_total_instructions = parse_execution_log_for_cumulative_instrs(pcore_execution_file)
            metrics['pcore_total_instructions'].append(pcore_total_instructions)
        else:
            metrics['pcore_total_instructions'].append(np.nan)

        if ecore_dirs:
            ecore_execution_file = os.path.join(ecore_dirs[0], "execution.log")
            ecore_total_instructions = parse_execution_log_for_cumulative_instrs(ecore_execution_file)
            metrics['ecore_total_instructions'].append(ecore_total_instructions)
        else:
            metrics['ecore_total_instructions'].append(np.nan)

    # Gather total instructions for each governor
    for governor in governors:
        governor_execution_file = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{governor}/execution.log"))
        if governor_execution_file:
            governor_total_instructions = parse_execution_log_for_cumulative_instrs(governor_execution_file[0])
            metrics['governors'][governor] = governor_total_instructions
        else:
            metrics['governors'][governor] = np.nan


    if metrics is None:
        print(f"Metrics not found for {application_name}")

    # Collect instruction data in the order of P-core, E-core, and governors
    instruction_data = metrics['pcore_total_instructions'] + metrics['ecore_total_instructions']
    instruction_data += [metrics['governors'][governor] for governor in governors]

    return np.nanmean(instruction_data)
    


def main():



    applications = config.parsec_apps # Add more applications as needed
    governors = ["performance", "powersave", "ondemand", "conservative", "schedutil"]

    output_dir = os.path.join(config.ROOTPATH, config.TESTING_FOLDER)
    os.makedirs(output_dir, exist_ok=True)

    for application_name in applications:
        print(f"{application_name} : {get_mean_instructions(application_name):.2e}")
        # Gather instruction data for the application
        metrics = gather_instruction_metrics(application_name, governors)
        if metrics is None:
            print(f"Metrics not found for {application_name}")
            continue

        # Collect instruction data in the order of P-core, E-core, and governors
        instruction_data = metrics['pcore_total_instructions'] + metrics['ecore_total_instructions']
        instruction_data += [metrics['governors'][governor] for governor in governors]

        # Plot the instruction comparisons for this application
        plot_total_instructions(application_name, instruction_data, output_dir)

        # Compute variance across all 15 runs
        total_variance = compute_variance(instruction_data)

        # Print or log the variance across all runs
        #print(f"Variance for total instructions across all 15 runs for {application_name}: {total_variance}")


if __name__ == "__main__":
    main()
