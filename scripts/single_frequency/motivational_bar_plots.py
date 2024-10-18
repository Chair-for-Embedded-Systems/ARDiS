import os
import re
import glob
import sys
import numpy as np
import matplotlib.pyplot as plt

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import config



# Enable LaTeX rendering in Matplotlib (if needed)
plt.rcParams.update({
    "text.usetex": True,  # Use LaTeX to render text
    "font.family": "serif",  # Use serif fonts
    "font.serif": ["Times"],  # Use Times font for the plot
    "axes.labelsize": 20,  # Font size for axis labels
    "axes.labelweight": "bold",  # Make axis labels bold
    "xtick.labelsize": 14,  # Font size for x-axis tick labels
    "ytick.labelsize": 18,  # Font size for y-axis tick labels
    "legend.fontsize": 18,  # Font size for the legend
    "axes.titlesize": 20  # Font size for the title
})


e_core_color = '#ABA8B2'
p_core_color = '#4C4B63'
mixed_core_color = '#F2C57C'

# Function to parse log file and accumulate instructions and energy
def parse_log_file(log_file, energy_type):
    time_points = []
    cumulative_instructions = []
    cumulative_energy = []

    with open(log_file, 'r') as file:
        cumulative_instr = 0
        cumulative_energy_value = 0
        for line in file:
            time_match = re.search(r'\[(\d+\.\d+)s\]', line)
            instr_match = re.search(r'instructions = (\d+)', line)
            energy_match = re.search(rf'power/energy-{energy_type}/ = (\d+)', line)

            if time_match and instr_match and energy_match:
                time = float(time_match.group(1))
                instructions = int(instr_match.group(1))
                energy = float(energy_match.group(1))/100

                cumulative_instr += instructions
                cumulative_energy_value += energy

                time_points.append(time)
                cumulative_instructions.append(cumulative_instr)
                cumulative_energy.append(cumulative_energy_value)
    
    return time_points, cumulative_instructions, cumulative_energy

# Function to gather metrics for each application at a given frequency and energy type
def gather_metrics(application_name, frequency, energy_type):
    log_directory = config.ANALYSIS_RESULTS_FOLDER

    # Use glob to find the directories matching the application name for P-core, E-core, and Mixed at the specified frequency
    pcore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Pcore"))
    ecore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Ecore"))
    mixed_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Mixed"))

    if not (pcore_dirs and ecore_dirs and mixed_dirs):
        return None

    # Take the first matching directory (assuming there's only one result per application)
    pcore_file = os.path.join(pcore_dirs[0], "periodic_counters.log")
    ecore_file = os.path.join(ecore_dirs[0], "periodic_counters.log")
    mixed_file = os.path.join(mixed_dirs[0], "periodic_counters.log")

    # Parse the logs
    ecore_time, ecore_instr, ecore_energy = parse_log_file(ecore_file, energy_type)
    pcore_time, pcore_instr, pcore_energy = parse_log_file(pcore_file, energy_type)
    mixed_time, mixed_instr, mixed_energy = parse_log_file(mixed_file, energy_type)

    # Calculate metrics for E-core
    ecore_total_time = ecore_time[-1]
    ecore_total_energy = ecore_energy[-1]
    ecore_total_instructions = ecore_instr[-1]

    # Calculate metrics for P-core
    pcore_total_time = pcore_time[-1]
    pcore_total_energy = pcore_energy[-1]
    pcore_total_instructions = pcore_instr[-1]

    # Calculate metrics for Mixed
    mixed_total_time = mixed_time[-1]
    mixed_total_energy = mixed_energy[-1]
    mixed_total_instructions = mixed_instr[-1]

    # Calculate the average number of instructions executed
    avg_instructions = (ecore_total_instructions + pcore_total_instructions + mixed_total_instructions) / 3

    # Calculate energy efficiency using the average instructions
    ecore_efficiency = (avg_instructions / ecore_total_energy) / 1e6 if ecore_total_energy > 0 else np.nan
    pcore_efficiency = (avg_instructions / pcore_total_energy) / 1e6 if pcore_total_energy > 0 else np.nan
    mixed_efficiency = (avg_instructions / mixed_total_energy) / 1e6 if mixed_total_energy > 0 else np.nan

    return {
        'ecore_time': ecore_total_time,
        'pcore_time': pcore_total_time,
        'mixed_time': mixed_total_time,
        'ecore_energy': ecore_total_energy,
        'pcore_energy': pcore_total_energy,
        'mixed_energy': mixed_total_energy,
        'ecore_efficiency': ecore_efficiency,
        'pcore_efficiency': pcore_efficiency,
        'mixed_efficiency': mixed_efficiency
    }

# Function to calculate percentage difference and add annotations
def annotate_bars(ax, ecore_values, pcore_values, mixed_values, index, bar_width, metric_type, applications):
    valid_apps = [ 'bodytrack', 'canneal', 'dedup', 'ferret', 'netdedup', 'netstreamcluster', 'lu_cb', 'lu_ncb', 'radix', 'water_nsquared', 'water_spatial']
    for i in range(len(ecore_values)):
        app_name = str(applications[i]).strip().lower()
        if app_name in valid_apps:
            print(f"Valid application found: {applications[i]}")
            if metric_type == 'efficiency':
                # Higher efficiency is better, compare to the max of E-core and P-core
                best_value = max(ecore_values[i], pcore_values[i])
                if best_value > 0:
                    improvement = ((mixed_values[i] - best_value) / best_value) * 100
            else:
                # Lower energy/time is better, compare to the min of E-core and P-core
                best_value = min(ecore_values[i], pcore_values[i])
                if best_value > 0:
                    improvement = ((best_value - mixed_values[i]) / best_value) * 100
            improvement_sign = '+' if improvement > 0 else '-'
            improvement_color = '#426A5A' if improvement > 0 else '#EF6F6C'
            improvement_y_shift = 5 if improvement > 0 else 15
            annotation = f"{improvement_sign}{improvement:.1f}\%"
            ax.text(index[i] + 1 * bar_width, mixed_values[i] + improvement_y_shift, annotation,
                    ha='center', va='bottom', fontsize=13, color=improvement_color, fontweight='bold')

# Function to generate the execution time plot
def plot_execution_time(applications, ecore_times, pcore_times, mixed_times, frequency, output_dir):
    plt.figure(figsize=(12, 6))
    bar_width = 0.25
    index = np.arange(len(applications))
    
    bars1 = plt.bar(index, ecore_times, bar_width, label='E-core', color=e_core_color)
    bars2 = plt.bar(index + bar_width, pcore_times, bar_width, label='P-core', color=p_core_color)
    bars3 = plt.bar(index + 2 * bar_width, mixed_times, bar_width, label='Mixed', color=mixed_core_color)
    
    plt.xlabel('Applications')
    plt.ylabel('Execution Time (s)')
    plt.title(f'Execution Time at {frequency}')
    plt.xticks(index + bar_width, applications, rotation=45, ha="right")
    plt.legend()

    # Annotate the bars with percentage differences
    #annotate_bars(plt, ecore_times, pcore_times, mixed_times, index, bar_width, metric_type='time')

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"execution_time_{frequency}.png"))
    plt.close()

# Function to generate energy plots for each energy type
def plot_energy(applications, ecore_values, pcore_values, mixed_values, metric_name, frequency, energy_type, output_dir):
    plt.figure(figsize=(12, 6))
    bar_width = 0.25
    index = np.arange(len(applications))
    
    bars1 = plt.bar(index, ecore_values, bar_width, label='E-core', color=e_core_color)
    bars2 = plt.bar(index + bar_width, pcore_values, bar_width, label='P-core', color=p_core_color)
    bars3 = plt.bar(index + 2 * bar_width, mixed_values, bar_width, label='Mixed', color=mixed_core_color)
    
    plt.xlabel('Applications')
    plt.ylabel(f'{metric_name} ({energy_type.capitalize()})')
    plt.title(f'{metric_name} at {frequency} ({energy_type})')
    plt.xticks(index + bar_width, applications, rotation=45, ha="right")
    plt.legend()

    # Annotate the bars with percentage differences
    metric_type = 'efficiency' if metric_name == 'Energy Efficiency' else 'energy'
    #annotate_bars(plt, ecore_values, pcore_values, mixed_values, index, bar_width, metric_type)

    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, f"{metric_name.lower()}_{energy_type}_{frequency}.png"))
    plt.close()


# Function to generate the execution time and energy plots in one figure
def plot_metrics_in_one_figure(applications, ecore_times, pcore_times, mixed_times,
                               ecore_energy, pcore_energy, mixed_energy,
                               ecore_efficiency, pcore_efficiency, mixed_efficiency,
                               frequency, energy_type, output_dir):
    fig, axs = plt.subplots(3, 1, figsize=(10, 10), sharex=True)  # Create 3 subplots, sharing the x-axis with smaller height
    
    bar_width = 0.25
    index = np.arange(len(applications))
    
    # Plot Execution Time
    axs[0].bar(index, ecore_times, bar_width, label='Static E-core', color=e_core_color, edgecolor='black')
    axs[0].bar(index + bar_width, pcore_times, bar_width, label='Static P-core', color=p_core_color, edgecolor='black')
    axs[0].bar(index + 2 * bar_width, mixed_times, bar_width, label='Sensitivity Aware', color=mixed_core_color, edgecolor='black')
    axs[0].set_ylabel('Execution Time (s)')
    axs[0].legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',
                      ncols=6, mode="expand", borderaxespad=0.)
    #annotate_bars(axs[0], ecore_times, pcore_times, mixed_times, index, bar_width, metric_type='time')

    # Plot Energy Consumption
    axs[1].bar(index, ecore_energy, bar_width, label='Static E-core', color=e_core_color, edgecolor='black')
    axs[1].bar(index + bar_width, pcore_energy, bar_width, label='Static P-core', color=p_core_color, edgecolor='black')
    axs[1].bar(index + 2 * bar_width, mixed_energy, bar_width, label='Sensitivity Aware', color=mixed_core_color, edgecolor='black')
    axs[1].set_ylabel('Energy (J)')
    #axs[1].legend()
    #annotate_bars(axs[1], ecore_energy, pcore_energy, mixed_energy, index, bar_width, metric_type='energy')

    # Plot Energy Efficiency
    axs[2].bar(index, ecore_efficiency, bar_width, label='Static E-core', color=e_core_color, edgecolor='black')
    axs[2].bar(index + bar_width, pcore_efficiency, bar_width, label='Static P-core', color=p_core_color, edgecolor='black')
    axs[2].bar(index + 2 * bar_width, mixed_efficiency, bar_width, label='Sensitivity Aware', color=mixed_core_color, edgecolor='black')
    axs[2].set_ylabel('Energy Efficiency (IPJ)')
    #axs[2].set_ylim(401)
    axs[2].set_ylim(0, 401) 
    #axs[2].legend()
    annotate_bars(axs[2], ecore_efficiency, pcore_efficiency, mixed_efficiency, index, bar_width, metric_type='efficiency', applications=[app.replace('parsec-', ' ').replace('splash2x.', '') for app in applications])

    # Set x-axis labels and ticks only for the bottom subplot
    axs[2].set_xlabel('Applications')
    axs[2].set_xticks(index + bar_width)
    axs[2].set_xticklabels([app.replace('parsec-', ' ').replace('splash2x.', '') for app in applications], rotation=45, ha="right")
    
    axs[0].grid(True, axis='both', which='both', linestyle='-', linewidth=1.2, color='#000', alpha=0.2)
    axs[1].grid(True, axis='both', which='both', linestyle='-', linewidth=1.2, color='#000', alpha=0.2)
    axs[2].grid(True, axis='both', which='both', linestyle='-', linewidth=1.2, color='#000', alpha=0.2)
    plt.tight_layout(pad=1.0)
    plt.savefig(os.path.join(output_dir, f"analysis_{frequency}.pdf"), dpi=300, format='pdf')
    plt.close()


def main():
    energy_types = ["psys",]
    frequencies = ["2500MHz",]
    applications = config.parsec_apps

    output_dir = os.path.join(config.ROOTPATH, f"{config.PAPERPLOT_FOLDER}/bars")
    os.makedirs(output_dir, exist_ok=True)

    for frequency in frequencies:
        ecore_times = []
        pcore_times = []
        mixed_times = []
        ecore_energy = {et: [] for et in energy_types}
        pcore_energy = {et: [] for et in energy_types}
        mixed_energy = {et: [] for et in energy_types}
        ecore_efficiency = {et: [] for et in energy_types}
        pcore_efficiency = {et: [] for et in energy_types}
        mixed_efficiency = {et: [] for et in energy_types}

        for application_name in applications:
            # Gather execution time
            metrics = gather_metrics(application_name, frequency, energy_types[0])  # Any energy type works for time
            if metrics is None:
                continue

            ecore_times.append(metrics['ecore_time'])
            pcore_times.append(metrics['pcore_time'])
            mixed_times.append(metrics['mixed_time'])

            # Gather energy and efficiency metrics
            for energy_type in energy_types:
                metrics = gather_metrics(application_name, frequency, energy_type)
                ecore_energy[energy_type].append(metrics['ecore_energy'])
                pcore_energy[energy_type].append(metrics['pcore_energy'])
                mixed_energy[energy_type].append(metrics['mixed_energy'])
                ecore_efficiency[energy_type].append(metrics['ecore_efficiency'])
                pcore_efficiency[energy_type].append(metrics['pcore_efficiency'])
                mixed_efficiency[energy_type].append(metrics['mixed_efficiency'])

        # Generate combined plot with 3 subfigures
        for energy_type in energy_types:
            plot_metrics_in_one_figure(applications, ecore_times, pcore_times, mixed_times,
                                       ecore_energy[energy_type], pcore_energy[energy_type], mixed_energy[energy_type],
                                       ecore_efficiency[energy_type], pcore_efficiency[energy_type], mixed_efficiency[energy_type],
                                       frequency, energy_type, output_dir)
if __name__ == "__main__":
    main()
