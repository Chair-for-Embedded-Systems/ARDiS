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
def gather_metrics(application_name, frequencies, local_mixed_folder):
    # Paths for periodic and execution logs
    print(local_mixed_folder)
    print(config.PARSEC_FIXED_FREQ_FOLDER)
    pcore_dirs = [glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{freq}MHz_Pcore")) for freq in frequencies]
    ecore_dirs = [glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{freq}MHz_Ecore")) for freq in frequencies]
    mixed_dirs = glob.glob(os.path.join(local_mixed_folder, f"*_{application_name}_Mixed*"))

    if not (pcore_dirs and ecore_dirs and mixed_dirs):
        return None

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

    # Parse the mixed periodic logs
    mixed_periodic_file = os.path.join(mixed_dirs[0], periodic_log_name)
    mixed_instructions, mixed_energy, _, _ = parse_periodic_log(mixed_periodic_file)
    metrics['periodic']['mixed'] = {'instructions': mixed_instructions, 'energy': mixed_energy}

    # Parse the execution logs for each frequency on P-cores and E-cores
    for i, freq in enumerate(frequencies):
        pcore_execution_file = os.path.join(pcore_dirs[i][0], execution_log_name)
        ecore_execution_file = os.path.join(ecore_dirs[i][0], execution_log_name)

        pcore_time, pcore_total_instructions, pcore_energy, _ = parse_execution_log(pcore_execution_file)
        ecore_time, ecore_total_instructions, ecore_energy, _ = parse_execution_log(ecore_execution_file)

        metrics['execution'][f'pcore_{freq}'] = {'instructions': pcore_total_instructions, 'energy': pcore_energy}
        metrics['execution'][f'ecore_{freq}'] = {'instructions': ecore_total_instructions, 'energy': ecore_energy}

    # Parse the mixed execution logs
    mixed_execution_file = os.path.join(mixed_dirs[0], execution_log_name)
    mixed_time, mixed_total_instructions, mixed_energy, _ = parse_execution_log(mixed_execution_file)
    metrics['execution']['mixed'] = {'instructions': mixed_total_instructions, 'energy': mixed_energy}

    return metrics

# Function to generate LaTeX table with highlighted maximum value in each row
def generate_latex_table(metric_data, metric_number, caption, local_mixed_folder, frequencies):
    # Extract the part of the string after 'mixed_' and before the last '/'
    schedule_info = local_mixed_folder.split("mixed_")[1].strip('/')

    # Form the sentence using the extracted information
    slice_info = schedule_info.split("_")[0]  # '1e9'
    optimization_info = schedule_info.split("_")[1]  # 'ipj'
    latex_code = "\\begin{table*}[htbp]\n"  # Use table* for full width in two-column documents
    latex_code += "\\centering\n"
    latex_code += f"\\caption{{With slices of length {slice_info} instructions, optimizing {optimization_info.upper()}, the tables provides a comparison of system energy efficiency using Metric {metric_number}: {caption}}}\n"
    latex_code += "\\begin{tabularx}{\\textwidth}{l|X" + "|X" * (len(frequencies)*2 + 1) + "}\n"  # 5 Pcore, 5 Ecore, 1 Mixed
    latex_code += "\\hline\n"
    
    # Convert frequencies from MHz to GHz and apply the line break
    frequency_labels = [f"P Core\\\\{int(freq)/1000:.1f}GHz" for freq in frequencies] + \
                       [f"E Core\\\\{int(freq)/1000:.1f}GHz" for freq in frequencies]
                       
    latex_code += "Application & Mixed & " + " & ".join(frequency_labels) + " \\\\\n"
    latex_code += "\\hline\n"

    for app_name, data in metric_data.items():
        # Find the maximum value in the row (excluding the first element which is the app name)
        max_value = max(data)
        # Build the row, highlighting the max value
        row = [f"\\cellcolor{{yellow}}{val:.2f}" if val == max_value else f"{val:.2f}" for val in data]
        latex_code += f"{app_name} & " + " & ".join(row) + " \\\\\n"

    latex_code += "\\hline\n"
    latex_code += "\\end{tabularx}\n"
    latex_code += "\\end{table*}\n"

    return latex_code

# Function to plot grouped bars for all applications and annotate improvements
def plot_grouped_metrics_with_improvement(metric_data, frequencies, metric_number, local_mixed_folder, metric_label):
    # Define colors for P-cores, E-cores, and mixed execution
    colors = {
        "mixed": "red",
        "P Core": ["#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd"],  # Different colors for each P-core frequency
        "E Core": ["#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"]   # Different colors for each E-core frequency
    }

    # Extract the application names and corresponding data
    app_names = list(metric_data.keys())
    num_apps = len(app_names)

    # Create a figure for the plot
    plt.figure(figsize=(12, 6))

    # Generate indices for each application on the x-axis
    indices = np.arange(num_apps)
    
    # Bar width and position offset for grouped bars
    bar_width = 0.07
    offset = np.arange(-5, 6) * bar_width  # Adjusted to handle 11 elements (1 mixed + 5 P-core + 5 E-core)

    # Store improvements for all applications
    improvements = []

    # Plot bars for each application and frequency
    for i, app_name in enumerate(app_names):
        # Get the data for the current application
        data = metric_data[app_name]

        # Ensure data has exactly 11 elements (1 mixed + 5 P-core + 5 E-core)
        if len(data) != 11:
            print(f"Error: Expected 11 data points, but got {len(data)} for application {app_name}. Skipping this application.")
            continue

        # Plot the mixed execution bar (first in the list)
        plt.bar(indices[i] + offset[0], data[0], bar_width, label="Mixed" if i == 0 else "", color=colors["mixed"])

        # Plot the bars for P-core frequencies
        for j, freq in enumerate(frequencies):
            plt.bar(indices[i] + offset[j+1], data[j+1], bar_width, label=f"P Core {int(freq)/1000:.1f}GHz" if i == 0 else "", color=colors["P Core"][j])

        # Plot the bars for E-core frequencies
        for j, freq in enumerate(frequencies):
            plt.bar(indices[i] + offset[j+6], data[j+6], bar_width, label=f"E Core {int(freq)/1000:.1f}GHz" if i == 0 else "", color=colors["E Core"][j])

        # Calculate the highest value among P-core and E-core executions
        max_value = max(data[1:])  # Skip the mixed execution value (data[0])
        mixed_value = data[0]

        # Calculate the improvement (percentage)
        improvement = ((mixed_value - max_value) / max_value) * 100 if max_value > 0 else 0
        improvements.append(improvement)

        # Annotate the plot with the individual improvement
        plt.text(indices[i], mixed_value + 1, f'{improvement:.2f}%', ha='center', va='bottom', fontsize=10)

    # Calculate max and mean improvement across all applications
    max_improvement = max(improvements)
    mean_improvement = np.mean(improvements)

    # Set the x-ticks and labels
    plt.xticks(indices, app_names, rotation=45, ha="right")
    plt.ylabel(metric_label)
    plt.title(f'Metric {metric_number}: {metric_label}\nMax Improvement: {max_improvement:.2f}% | Mean Improvement: {mean_improvement:.2f}%')
    
    # Add a legend (only once)
    plt.legend(loc="upper right", bbox_to_anchor=(1.15, 1), fontsize='small')

    # Save the plot
    plot_file = os.path.join(local_mixed_folder, f'metric_{metric_number}_grouped_plot.png')
    plt.tight_layout()
    plt.savefig(plot_file)
    plt.close()

    print(f"Grouped plot saved for Metric {metric_number} as {plot_file}")




# Function to compute metrics for all applications
def compute_metrics_for_all(applications, frequencies, local_mixed_folder):
    metric1_data = {}
    metric2_data = {}

    for application in applications:
        metrics = gather_metrics(application, frequencies, local_mixed_folder)
        if metrics is None:
            print(f"Metrics not found for {application}")
            continue

        # Metric 1: Instantaneous IPJ (Mean Efficiency)
        mixed_ipj_1 = compute_ipj(metrics['periodic']['mixed']['instructions'], metrics['periodic']['mixed']['energy'])
        pcore_ipjs_1 = [compute_ipj(metrics['periodic'][f'pcore_{freq}']['instructions'], metrics['periodic'][f'pcore_{freq}']['energy']) for freq in frequencies]
        ecore_ipjs_1 = [compute_ipj(metrics['periodic'][f'ecore_{freq}']['instructions'], metrics['periodic'][f'ecore_{freq}']['energy']) for freq in frequencies]

        # Metric 2: Mean IPJ (Mean of instructions / mean of energy)
        mixed_ipj_2 = compute_ipj(metrics['periodic']['mixed']['instructions'], metrics['periodic']['mixed']['energy'])
        pcore_ipjs_2 = [compute_ipj(metrics['periodic'][f'pcore_{freq}']['instructions'], metrics['periodic'][f'pcore_{freq}']['energy']) for freq in frequencies]
        ecore_ipjs_2 = [compute_ipj(metrics['periodic'][f'ecore_{freq}']['instructions'], metrics['periodic'][f'ecore_{freq}']['energy']) for freq in frequencies]

        # Store data in corresponding metric tables
        metric1_data[application] = [mixed_ipj_1] + pcore_ipjs_1 + ecore_ipjs_1
        metric2_data[application] = [mixed_ipj_2] + pcore_ipjs_2 + ecore_ipjs_2

    return metric1_data, metric2_data


def generate_latex_code(metric1_data, metric2_data, frequencies, local_mixed_folder):
    # Generate LaTeX tables
    latex_table_metric1 = generate_latex_table(metric1_data, 1, "Instantaneous IPJ as mean efficiency throughout the execution.", local_mixed_folder, frequencies)
    latex_table_metric2 = generate_latex_table(metric2_data, 2, "IPJ computed as mean instructions/mean energy.", local_mixed_folder, frequencies)

    # Save LaTeX tables to a file
    with open("comparison_tables.tex", "a") as f:
        f.write(latex_table_metric1)
        f.write("\n")
        f.write(latex_table_metric2)
        f.write("\n")

# Main function
def main():
    applications = config.parsec_apps
    frequencies = ["1500", "2000", "2500", "3000", "3500"]  # Example frequencies

    for local_mixed_folder in config.PARSEC_MIXED_STATIC_FOLDERS:
        # Compute metrics
        metric1_data, metric2_data = compute_metrics_for_all(applications, frequencies, local_mixed_folder)
        # Generate LaTeX tables
        generate_latex_code(metric1_data, metric2_data, frequencies, local_mixed_folder)
        # Plot the results
        #plot_grouped_metrics_with_improvement(metric1_data, frequencies, 1, local_mixed_folder, "Instantaneous IPJ")
        plot_grouped_metrics_with_improvement(metric2_data, frequencies, 2, local_mixed_folder, "Mean IPJ")
        

if __name__ == "__main__":
    main()
