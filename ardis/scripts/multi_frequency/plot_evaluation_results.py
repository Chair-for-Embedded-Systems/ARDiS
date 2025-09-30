import os
import re
import glob
import sys
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import colors as mcolors

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import ardis.config as config

# Enable LaTeX rendering in Matplotlib (if needed)
plt.rcParams.update({
    "text.usetex": True,  # Use LaTeX to render text
    "font.family": "serif",  # Use serif fonts
    "font.serif": ["Times"],  # Use Times font for the plot
    "axes.labelsize": 16,  # Font size for axis labels
    "axes.labelweight": "bold",  # Make axis labels bold
    "xtick.labelsize": 14,  # Font size for x-axis tick labels
    "ytick.labelsize": 14,  # Font size for y-axis tick labels
    "legend.fontsize": 16,  # Font size for the legend
    "axes.titlesize": 20  # Font size for the title
})

# Define colors
e_core_color = '#ABA8B2'
p_core_color = '#4C4B63'
mixed_base_color = '#F2C57C'

# Generate shades for mixed executions
mixed_shades = [mcolors.to_rgba(mixed_base_color, alpha) for alpha in np.linspace(0.6, 1.0, 4)]


# Function to parse periodic log and accumulate instructions and energy
def parse_log_file(log_file):
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


def gather_metrics(application_name, frequency, energy_type, mixed_folders):
    print(f"Processing {application_name} at {frequency}...")
    log_directory = config.PARSEC_FIXED_FREQ_FOLDER

    # Use glob to find the directories matching the application name for P-core and E-core at the specified frequency
    pcore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Pcore"))
    ecore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Ecore"))
    #print(pcore_dirs, ecore_dirs, mixed_folders)
    if not (pcore_dirs and ecore_dirs and mixed_folders):
        return None

    # Take the first matching directory (assuming there's only one result per application)
    pcore_file = os.path.join(pcore_dirs[0], "periodic_counters.log")
    ecore_file = os.path.join(ecore_dirs[0], "periodic_counters.log")

    # Parse the logs for P-core and E-core
    _, _, _, e_eff = parse_log_file(ecore_file)
    _, _, _, p_eff = parse_log_file(pcore_file)

    # Prepare mixed execution metrics
    mixed_metrics = []
    for mixed_folder in mixed_folders:
        
        mixed_file = os.path.join(glob.glob(os.path.join(mixed_folder, f"*_{application_name}*"))[0], "periodic_counters.log")
        _, _, _, mixed_efficiency = parse_log_file(mixed_file)
        mixed_metrics.append(mixed_efficiency)

    return {
        'ecore_efficiency': e_eff,
        'pcore_efficiency': p_eff,
        'mixed_efficiencies': mixed_metrics
    }

# Function to calculate percentage difference and add annotations
def annotate_bars(ax, pcore_values, mixed_values, index, bar_width, applications):
    valid_apps = config.parsec_apps
    #['bodytrack', 'canneal', 'dedup', 'ferret', 'netdedup', 'netstreamcluster', 'lu_cb', 'lu_ncb', 'radix', 'water_nsquared', 'water_spatial']

    for i in range(len(pcore_values)):
        app_name = str(applications[i]).strip().lower()
        print(app_name)
        if app_name in valid_apps:
            print(f"Valid application found: {applications[i]}")

            # Find the maximum mixed efficiency for the current application
            best_mixed_value = max(mixed_values[i])

            # Calculate the improvement relative to P-core efficiency
            pcore_value = pcore_values[i]
            if pcore_value > 0:
                improvement = ((best_mixed_value - pcore_value) / pcore_value) * 100

            # Determine annotation details based on the improvement
            improvement_sign = '+' if improvement > 0 else '-'
            improvement_color = '#426A5A' if improvement > 0 else '#EF6F6C'
            improvement_y_shift = 5 if improvement > 0 else 15
            annotation = f"{improvement_sign}{improvement:.1f}\%"

            # Add the annotation above the mixed bars for the application
            ax.text(index[i] + (2 * bar_width) + (bar_width/2),  # Positioning at the center of the mixed group
                    best_mixed_value + improvement_y_shift,  # Adjust Y position
                    annotation,
                    ha='center', va='bottom', fontsize=16, color=improvement_color, fontweight='bold')
        
def plot_energy_efficiency(applications, ecore_efficiency, pcore_efficiency, mixed_efficiencies, mixed_folders, frequency, output_dir):
    plt.figure(figsize=(13, 4))
    bar_width = 0.15  # Adjusted to fit more bars
    index = np.arange(len(applications))

    # Plot E-core and P-core energy efficiency bars
    plt.bar(index, ecore_efficiency, bar_width, label='P-core at 3.5GHz', color=e_core_color, edgecolor='black')
    plt.bar(index + bar_width, pcore_efficiency, bar_width, label='P-core at 3.5GHz', color=p_core_color, edgecolor='black')

    # Plot Mixed energy efficiency bars
    for i in range(len(mixed_efficiencies[0])):  # Loop over the number of granularities (4 in your case)
        mixed_eff = [eff[i] for eff in mixed_efficiencies]  # Extract the i-th efficiency for all applications
        slicing_granularity = os.path.basename(os.path.normpath(mixed_folders[i])).split('_')[1]  # Extract the granularity from the folder name
        slice_label = f"{float(slicing_granularity):.0e} slice"  # Format the granularity as "1e+09"
        
        # Ensure index + (i + 2) * bar_width has the same length as mixed_eff for broadcasting
        # Use viridis colormap for mixed efficiencies
        plasma = plt.cm.get_cmap('Wistia', len(mixed_efficiencies[0]))
        plt.bar(index + (i + 2) * bar_width, mixed_eff, bar_width, label=slice_label, color=plasma(i), edgecolor='black')
        #plt.bar(index + (i + 2) * bar_width, mixed_eff, bar_width, label=slice_label, color=viridis(i), edgecolor='black')
    
    annotate_bars(plt.gca(), pcore_efficiency, mixed_efficiencies, index, bar_width, applications)

    # Labels and legend
    #plt.xlabel('Applications')
    plt.ylabel('Energy Efficiency (IPJ)')
    plt.ylim(ymax=451)
    
    plt.grid(True, axis='both', which='both', linestyle='-', linewidth=1.2, color='#000', alpha=0.2)
    ##plt.title(f'Energy Efficiency at {frequency}')
    plt.xticks(index + (2*bar_width) + (bar_width/2), [app.replace("parsec-", "").replace("splash2x.","") for app in applications ], rotation=45, ha="right")
    plt.legend(bbox_to_anchor=(0., 1.02, 1., .102), loc='lower left',
                      ncols=6, mode="expand", borderaxespad=0.)

    plt.tight_layout(pad=1.0)
    plt.savefig(os.path.join(output_dir, f"evaluation_{frequency}.pdf"), dpi=300, format='pdf')
    plt.close()

def main():
    energy_type = "psys"  # Assuming psys energy type
    frequency = "3500MHz"  # Use 3500MHz for both P-core and E-core
    applications = config.parsec_apps  # List of applications
    mixed_folders = config.PARSEC_MIXED_STATIC_FOLDERS  # List of mixed execution folders

    output_dir = os.path.join(config.ROOTPATH, f"{config.PAPERPLOT_FOLDER}/bars")
    os.makedirs(output_dir, exist_ok=True)

    ecore_efficiency = []
    pcore_efficiency = []
    mixed_efficiency = []

    for application_name in applications:
        # Gather energy efficiency metrics
        metrics = gather_metrics(application_name, frequency, energy_type, mixed_folders)
        if metrics is None:
            continue

        ecore_efficiency.append(metrics['ecore_efficiency'])
        pcore_efficiency.append(metrics['pcore_efficiency'])
        mixed_efficiency.append(metrics['mixed_efficiencies'])
    print(len(mixed_efficiency))
    # Plot energy efficiency for the given applications
    plot_energy_efficiency(applications, ecore_efficiency, pcore_efficiency, mixed_efficiency, mixed_folders, frequency, output_dir)

if __name__ == "__main__":
    main()
