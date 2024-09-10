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
def gather_metrics(application_name, frequency, governors, local_mixed_folder):
    # Paths for periodic and execution logs
    pcore_dirs = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{frequency}_Pcore"))
    mixed_dirs = glob.glob(os.path.join(local_mixed_folder, f"*_{application_name}_Mixed*"))

    if not (pcore_dirs and mixed_dirs):
        return None

    # Assume both log files are named as follows:
    periodic_log_name = "periodic_counters.log"
    execution_log_name = "execution.log"

    # Initialize a dictionary to hold all the retrieved data
    metrics = {
        'periodic': {},
        'execution': {}
    }

    # Parse the periodic logs
    pcore_periodic_file = os.path.join(pcore_dirs[0], periodic_log_name)
    mixed_periodic_file = os.path.join(mixed_dirs[0], periodic_log_name)

    pcore_periodic_instructions, pcore_periodic_energy, pcore_mean_energy, pcore_mean_efficiency = parse_periodic_log(pcore_periodic_file)
    mixed_periodic_instructions, mixed_periodic_energy, mixed_mean_energy, mixed_mean_efficiency = parse_periodic_log(mixed_periodic_file)

    metrics['periodic']['pcore_instructions'] = pcore_periodic_instructions
    metrics['periodic']['pcore_energy'] = pcore_periodic_energy
    metrics['periodic']['mixed_instructions'] = mixed_periodic_instructions
    metrics['periodic']['mixed_energy'] = mixed_periodic_energy

    # Parse the execution logs
    pcore_execution_file = os.path.join(pcore_dirs[0], execution_log_name)
    mixed_execution_file = os.path.join(mixed_dirs[0], execution_log_name)

    pcore_execution_time, pcore_total_instructions, pcore_execution_energy, pcore_cumulative_instructions = parse_execution_log(pcore_execution_file)
    mixed_execution_time, mixed_total_instructions, mixed_execution_energy, mixed_cumulative_instructions = parse_execution_log(mixed_execution_file)

    metrics['execution']['pcore_total_instructions'] = pcore_total_instructions
    metrics['execution']['pcore_total_energy'] = pcore_execution_energy
    metrics['execution']['mixed_total_instructions'] = mixed_total_instructions
    metrics['execution']['mixed_total_energy'] = mixed_execution_energy

    # Parse the logs for each governor
    for governor in governors:
        governor_periodic_file = glob.glob(os.path.join(config.PARSEC_GOVERNOR_FOLDER, f"*_{application_name}_{governor}/periodic_counters.log"))
        governor_execution_file = glob.glob(os.path.join(config.PARSEC_GOVERNOR_FOLDER, f"*_{application_name}_{governor}/execution.log"))

        if governor_periodic_file:
            gov_periodic_instructions, gov_periodic_energy, gov_mean_energy, gov_mean_efficiency = parse_periodic_log(governor_periodic_file[0])
            metrics['periodic'][governor] = {'instructions': gov_periodic_instructions, 'energy': gov_periodic_energy}

        if governor_execution_file:
            gov_execution_time, gov_total_instructions, gov_execution_energy, gov_cumulative_instructions = parse_execution_log(governor_execution_file[0])
            metrics['execution'][governor] = {'instructions': gov_total_instructions, 'energy': gov_execution_energy}

    return metrics
# Function to generate LaTeX table with highlighted maximum value in each row
def generate_latex_table(metric_data, metric_number, caption, local_mixed_folder):
    # Extract the part of the string after 'mixed_' and before the last '/'
    schedule_info = local_mixed_folder.split("mixed_")[1].strip('/')

    # Form the sentence using the extracted information
    slice_info = schedule_info.split("_")[0]  # '1e9'
    optimization_info = schedule_info.split("_")[1]  # 'ipj'
    latex_code = "\\begin{table*}[htbp]\n"  # Use table* for full width in two-column documents
    latex_code += "\\centering\n"
    latex_code += f"\\caption{{With slices of length {slice_info} instructions, optimizing {optimization_info.upper()}, the tables provides a comparison of system energy efficiency using Metric {metric_number}: {caption}}}\n"
    latex_code += "\\begin{tabularx}{\\textwidth}{l|X|X|X|X|X|X|X}\n"  # Use tabularx with \textwidth for full width
    latex_code += "\\hline\n"
    latex_code += "Application & Ours (Mixed) & Max Freq & Performance & Ondemand & Schedutil & Powersave & Conservative \\\\\n"
    latex_code += "\\hline\n"

    for app_name, data in metric_data.items():
        # Find the maximum value in the row (excluding the first element which is the app name)
        max_value = max(data)
        # Build the row, highlighting the max value
        row = [f"\\cellcolor{{yellow}}{val:.2f}" if val == max_value else f"{val:.2f}" for val in data]
        latex_code += f"{app_name} & " + " & ".join(row) + " \\\\\n"

    latex_code += "\\hline\n"
    latex_code += "\\end{tabularx}\n"
    latex_code += "\\end{table*}\n"  # Use table* for full width

    return latex_code


# Function to compute metrics for all applications
def compute_metrics_for_all(applications, governors, local_mixed_folder):
    metric1_data = {}
    metric2_data = {}
    metric3_data = {}
    metric4_data = {}

    for application in applications:
        metrics = gather_metrics(application, "3500MHz", governors, local_mixed_folder)
        if metrics is None:
            print(f"Metrics not found for {application}")
            continue

        # Metric 1: Instantaneous IPJ (Mean Efficiency)
        mixed_ipj_1 = compute_ipj(metrics['periodic']['mixed_instructions'], metrics['periodic']['mixed_energy'])
        pcore_ipj_1 = compute_ipj(metrics['periodic']['pcore_instructions'], metrics['periodic']['pcore_energy'])
        governor_ipjs_1 = [compute_ipj(metrics['periodic'][gov]['instructions'], metrics['periodic'][gov]['energy']) for gov in governors]

        # Metric 2: Mean IPJ (Mean of instructions / mean of energy)
        mixed_ipj_2 = compute_ipj(metrics['periodic']['mixed_instructions'], metrics['periodic']['mixed_energy'])
        pcore_ipj_2 = compute_ipj(metrics['periodic']['pcore_instructions'], metrics['periodic']['pcore_energy'])
        governor_ipjs_2 = [compute_ipj(metrics['periodic'][gov]['instructions'], metrics['periodic'][gov]['energy']) for gov in governors]

        # Metric 3: Cumulative Instructions / Total Energy
        mixed_ipj_3 = compute_ipj(metrics['execution']['mixed_total_instructions'], metrics['execution']['mixed_total_energy'])
        pcore_ipj_3 = compute_ipj(metrics['execution']['pcore_total_instructions'], metrics['execution']['pcore_total_energy'])
        governor_ipjs_3 = [compute_ipj(metrics['execution'][gov]['instructions'], metrics['execution'][gov]['energy']) for gov in governors]

        # Metric 4: Total Instructions / Total Energy
        mixed_ipj_4 = compute_ipj(metrics['execution']['mixed_total_instructions'], metrics['execution']['mixed_total_energy'])
        pcore_ipj_4 = compute_ipj(metrics['execution']['pcore_total_instructions'], metrics['execution']['pcore_total_energy'])
        governor_ipjs_4 = [compute_ipj(metrics['execution'][gov]['instructions'], metrics['execution'][gov]['energy']) for gov in governors]

        # Store data in corresponding metric tables
        metric1_data[application] = [mixed_ipj_1, pcore_ipj_1] + governor_ipjs_1
        metric2_data[application] = [mixed_ipj_2, pcore_ipj_2] + governor_ipjs_2
        metric3_data[application] = [mixed_ipj_3, pcore_ipj_3] + governor_ipjs_3
        metric4_data[application] = [mixed_ipj_4, pcore_ipj_4] + governor_ipjs_4

    return metric1_data, metric2_data, metric3_data, metric4_data

# Main function
def main():
    applications = config.parsec_apps
    governors = ["performance", "powersave", "ondemand", "conservative", "schedutil"]


    for local_mixed_folder in config.PARSEC_MIXED_STATIC_FOLDERS:
        # Compute metrics
        metric1_data, metric2_data, metric3_data, metric4_data = compute_metrics_for_all(applications, governors, local_mixed_folder)

        # Generate LaTeX tables
        latex_table_metric1 = generate_latex_table(metric1_data, 1, "Instantaneous IPJ as mean efficiency throughout the execution.", local_mixed_folder)
        latex_table_metric2 = generate_latex_table(metric2_data, 2, "IPJ computed as mean instructions/mean energy.", local_mixed_folder)
        latex_table_metric3 = generate_latex_table(metric3_data, 3, "Cumulative instructions divided by total energy.", local_mixed_folder)
        latex_table_metric4 = generate_latex_table(metric4_data, 4, "Total instructions divided by total energy.", local_mixed_folder)

        # Save LaTeX tables to a file
        with open("comparison_tables.tex", "a") as f:
            f.write(latex_table_metric1)
            f.write("\n")
            f.write(latex_table_metric2)
            f.write("\n")
            f.write(latex_table_metric3)
            f.write("\n")
            f.write(latex_table_metric4)

if __name__ == "__main__":
    main()
