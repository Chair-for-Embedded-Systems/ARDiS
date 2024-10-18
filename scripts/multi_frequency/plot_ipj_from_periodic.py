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

# Function to parse the one-shot execution log and retrieve cumulative instructions, energy, and time
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

# Function to compute Energy Delay Product (EDP)
def compute_ipj(energy, instructions):
    return (instructions / energy) * 1e-6 if energy > 0 else np.nan

# Function to gather metrics for P-core, Mixed-core, and all governors from both periodic and execution logs
def gather_metrics(application_name, frequency, governors):
    # Paths for periodic and execution logs
    pcore_dirs = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{frequency}_Pcore"))
    mixed_dirs = glob.glob(os.path.join(config.PARSEC_MIXED_STATIC_FOLDER_2E9, f"*_{application_name}_Mixed"))

    if not (pcore_dirs and mixed_dirs):
        return None

    # Assume both log files are named as follows:
    periodic_log_name = "periodic_counters.log"
    execution_log_name = "execution.log"

    # Initialize a dictionary to hold all the retrieved data
    metrics = {
        'periodic': {
            'pcore_instructions': None,
            'pcore_energy': None,
            'pcore_mean_energy': None,
            'pcore_mean_efficiency': None,
            'mixed_instructions': None,
            'mixed_energy': None,
            'mixed_mean_energy': None,
            'mixed_mean_efficiency': None,
            'governors': {}
        },
        'execution': {
            'pcore_cumulative_instructions': None,
            'pcore_total_instructions': None,
            'pcore_total_energy': None,
            'pcore_total_time': None,
            'mixed_cumulative_instructions': None,
            'mixed_total_instructions': None,
            'mixed_total_energy': None,
            'mixed_total_time': None,
            'governors': {}
        }
    }

    # Parse the periodic logs
    pcore_periodic_file = os.path.join(pcore_dirs[0], periodic_log_name)
    mixed_periodic_file = os.path.join(mixed_dirs[0], periodic_log_name)

    pcore_periodic_instructions, pcore_periodic_energy, pcore_mean_energy, pcore_mean_efficiency = parse_periodic_log(pcore_periodic_file)
    mixed_periodic_instructions, mixed_periodic_energy, mixed_mean_energy, mixed_mean_efficiency = parse_periodic_log(mixed_periodic_file)

    metrics['periodic']['pcore_instructions'] = pcore_periodic_instructions
    metrics['periodic']['pcore_energy'] = pcore_periodic_energy
    metrics['periodic']['pcore_mean_energy'] = pcore_mean_energy
    metrics['periodic']['pcore_mean_efficiency'] = pcore_mean_efficiency
    metrics['periodic']['mixed_instructions'] = mixed_periodic_instructions
    metrics['periodic']['mixed_energy'] = mixed_periodic_energy
    metrics['periodic']['mixed_mean_energy'] = mixed_mean_energy
    metrics['periodic']['mixed_mean_efficiency'] = mixed_mean_efficiency

    # Parse the execution logs
    pcore_execution_file = os.path.join(pcore_dirs[0], execution_log_name)
    mixed_execution_file = os.path.join(mixed_dirs[0], execution_log_name)

    pcore_execution_time, pcore_total_instructions, pcore_execution_energy, pcore_cumulative_instructions = parse_execution_log(pcore_execution_file)
    mixed_execution_time, mixed_total_instructions, mixed_execution_energy, mixed_cumulative_instructions = parse_execution_log(mixed_execution_file)

    metrics['execution']['pcore_cumulative_instructions'] = pcore_cumulative_instructions
    metrics['execution']['pcore_total_instructions'] = pcore_total_instructions
    metrics['execution']['pcore_total_energy'] = pcore_execution_energy
    metrics['execution']['pcore_total_time'] = pcore_execution_time

    metrics['execution']['mixed_cumulative_instructions'] = mixed_cumulative_instructions
    metrics['execution']['mixed_total_instructions'] = mixed_total_instructions
    metrics['execution']['mixed_total_energy'] = mixed_execution_energy
    metrics['execution']['mixed_total_time'] = mixed_execution_time

    # Parse the logs for each governor
    for governor in governors:
        governor_periodic_file = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{governor}/periodic_counters.log"))
        governor_execution_file = glob.glob(os.path.join(config.PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{governor}/execution.log"))

        if governor_periodic_file:
            gov_periodic_instructions, gov_periodic_energy, gov_mean_energy, gov_mean_efficiency = parse_periodic_log(governor_periodic_file[0])
            metrics['periodic']['governors'][governor] = {
                'instructions': gov_periodic_instructions,
                'energy': gov_periodic_energy,
                'gov_mean_efficiency': gov_mean_efficiency,
                'mean_energy': gov_mean_energy
            }

        if governor_execution_file:
            gov_execution_time, gov_total_instructions, gov_execution_energy, gov_cumulative_instructions = parse_execution_log(governor_execution_file[0])
            metrics['execution']['governors'][governor] = {
                'cumulative_instructions': gov_cumulative_instructions,
                'total_instructions': gov_total_instructions,
                'energy': gov_execution_energy,
                'time': gov_execution_time
            }

    return metrics
# Function to compute percentage improvement
def compute_improvement(mixed_ipj, performance_ipj):
    if performance_ipj > 0:
        improvement = ((mixed_ipj - performance_ipj) / performance_ipj) * 100
        return improvement
    return np.nan

# Function to plot EDP for all run types and display percentage increase for mixed over performance
def plot_edp(applications, edps, frequency, output_dir):
    plt.figure(figsize=(12, 6))
    bar_width = 0.1
    index = np.arange(len(applications))

    labels = ['P-core max', 'Mixed', 'performance', 'powersave', 'ondemand', 'conservative', 'schedutil']
    colors = ['blue', 'green', 'red', 'orange', 'purple', 'brown', 'black']

    # Initialize lists to track improvements
    improvements = []

    for i, label in enumerate(labels):
        plt.bar(index + i * bar_width, [app[i] for app in edps], bar_width, label=label, color=colors[i], alpha=0.7)

    # Annotate the mixed-core bars with the percentage improvement over the performance governor
    for idx, application_name in enumerate(applications):
        mixed_ipj = edps[idx][1]  # Mixed-core IPJ
        performance_ipj = edps[idx][2]  # Performance governor IPJ

        # Compute percentage improvement
        improvement = compute_improvement(mixed_ipj, performance_ipj)
        improvements.append(improvement)

        # Add annotation on top of mixed-core bar
        #plt.text(index[idx] + bar_width, mixed_ipj + 0.02, f'{improvement:.1f}%', ha='center', color='black')

    # Compute average and max improvement
    valid_improvements = [imp for imp in improvements if not np.isnan(imp)]  # Filter out NaN values
    avg_improvement = np.mean(valid_improvements) if valid_improvements else 0
    max_improvement = np.max(valid_improvements) if valid_improvements else 0

    # Display average and max improvements in the plot title or as a separate log message
    plt.title(f'IPJ Comparison (Avg improvement: {avg_improvement:.1f}%, Max improvement: {max_improvement:.1f}%)')

    plt.xlabel('Applications')
    plt.ylabel('Energy Efficiency (MI/J)')
    plt.xticks(index + 1.5 * bar_width, applications, rotation=45, ha="right")
    plt.legend()

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"ipj_comparison_periodic_mean_efficiency.png"))
    plt.close()

    # Print or log the average and max improvements for further analysis
    print(f'Average improvement across all applications: {avg_improvement:.1f}%')
    print(f'Maximum improvement across all applications: {max_improvement:.1f}%')




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
    



# Main function to retrieve, compute EDP, and plot results
def main():
    applications = config.parsec_apps
    #applications = ["parsec-blackscholes",]
    frequency = "3500MHz"
    governors = ["performance","powersave","ondemand","conservative","schedutil"]
    
    output_dir = os.path.join(config.ROOTPATH, f"{config.EVALUATION_FOLDER}/plots/bars")
    os.makedirs(output_dir, exist_ok=True)
    
    ipjs = []
    
    for application_name in applications:
        mean_instructions = get_mean_instructions(application_name)
        metrics = gather_metrics(application_name, frequency, governors)
        if metrics is None:
            print(f"Metrics not found for {application_name} at {frequency}")
            continue

        pcore_ipj = compute_ipj(metrics['periodic']['pcore_energy'], mean_instructions)
        mixed_ipj = compute_ipj(metrics['periodic']['mixed_energy'], mean_instructions)
        #pcore_ipj = metrics['periodic']['pcore_mean_efficiency']
        #mixed_ipj = metrics['periodic']['mixed_mean_efficiency']

        app_ipjs = [pcore_ipj, mixed_ipj]

        # Calculate EDP for each governor
        for governor in governors:
            governor_energy = metrics['periodic']['governors'][governor]['energy']
            governor_instructions = mean_instructions
            governor_ipj = compute_ipj(governor_energy, governor_instructions)
            #governor_ipj = metrics['periodic']['governors'][governor]['gov_mean_efficiency']
            app_ipjs.append(governor_ipj)
        
        ipjs.append(app_ipjs)

    # Plot the EDP results
    plot_edp(applications, ipjs, frequency, output_dir)

if __name__ == "__main__":
    main()
