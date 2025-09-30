import sys
import os
import re
import glob
from scipy.spatial import ConvexHull

import numpy as np
import matplotlib.pyplot as plt
import itertools
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
from ardis.config import *

# Enable LaTeX rendering in Matplotlib (if needed)
plt.rcParams.update({
    "text.usetex": True,  # Use LaTeX to render text
    "font.family": "serif",  # Use serif fonts
    "font.serif": ["Times"],  # Use Times font for the plot
    "axes.labelsize": 20,  # Font size for axis labels
    "axes.labelweight": "bold",  # Make axis labels bold
    "xtick.labelsize": 18,  # Font size for x-axis tick labels
    "ytick.labelsize": 18,  # Font size for y-axis tick labels
    "legend.fontsize": 16,  # Font size for the legend
    "axes.titlesize": 20,  # Font size for the title
})

# Adjusted function to parse execution log and retrieve instructions, energy, and time
def parse_execution_log(log_file):
    total_time = None
    total_energy = None
    total_instructions = None

    with open(log_file, 'r') as file:
        for line in file:
            if "Total time elapsed (perf)=" in line:
                total_time = float(re.search(r'Total time elapsed \(perf\)= (\d+\.\d+)', line).group(1))
            if "Total instructions executed =" in line:
                total_instructions = int(re.search(r'Total instructions executed = (\d+)', line).group(1))
            if "Total energy consumed (perf)=" in line:
                total_energy = float(re.search(r'Total energy consumed \(perf\)= (\d+\.\d+)', line).group(1))
    
    return total_time, total_instructions, total_energy


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



# Adjusted function to gather metrics for P-core and E-core results across frequencies
def gather_metrics(application_name, frequency, core_type):
    core_dirs = glob.glob(os.path.join(PARSEC_FIXED_FREQ_FOLDER, f"*_{application_name}_{frequency}_{core_type}"))
    
    if not core_dirs:
        return None

    log_file = os.path.join(core_dirs[0], "execution.log")
    time, _, _ = parse_execution_log(os.path.join(core_dirs[0], "execution.log"))

    
    _, _, _, efficieny = parse_periodic_log(os.path.join(core_dirs[0], "periodic_counters.log"))
    
    return time, efficieny
# Function to normalize the energy efficiency values
def normalize_efficiency(efficiency, max_efficiency):
    return efficiency / max_efficiency if max_efficiency > 0 else np.nan

# Function to normalize the execution time values
def normalize_execution_time(execution_time, min_execution_time):
    return execution_time / min_execution_time if min_execution_time > 0 else np.nan

# Function to draw a convex hull around a set of points
# Function to fill the convex hull area with a background color
def fill_convex_hull(points, ax, color, alpha=0.2):
    if len(points) < 3:
        return  # A convex hull requires at least 3 points
    hull = ConvexHull(points)
    hull_points = np.append(hull.vertices, hull.vertices[0])  # Close the hull

    # Extract the x and y coordinates for the hull
    hull_x = points[hull_points, 0]
    hull_y = points[hull_points, 1]
    
    # Fill the hull area with the specified color and alpha transparency
    ax.fill(hull_x, hull_y, color=color, alpha=alpha)

from scipy.interpolate import splprep, splev

# Function to create a smooth (rounded) convex hull and fill it
def fill_rounded_convex_hull(points, ax, color, alpha=0.2, smooth_factor=100):
    if len(points) < 3:
        return  # A convex hull requires at least 3 points

    # Compute the convex hull
    hull = ConvexHull(points)
    hull_points = points[hull.vertices]
    
    # Close the polygon by repeating the first point at the end
    hull_points = np.vstack([hull_points, hull_points[0]])

    # Use splprep and splev to create smooth curves between the hull points
    tck, u = splprep([hull_points[:, 0], hull_points[:, 1]], s=0, per=True)
    smooth_hull = splev(np.linspace(0, 1, smooth_factor), tck)
    
    # Fill the smooth convex hull area
    ax.fill(smooth_hull[0], smooth_hull[1], color=color, alpha=alpha)

# Function to generate scatter plot for normalized energy efficiency vs normalized execution time
# for specific applications, with each application in a subfigure (2x2 grid)
def plot_normalized_efficiency_vs_time_with_rounded_subplots(applications, results, output_dir, frequencies):
    fig, axs = plt.subplots(2, 2, figsize=(9, 8))  # 2x2 grid of subplots
    axs = axs.flatten()  # Flatten the 2D array to 1D for easier indexing

    # Define markers for core types
    pcore_marker = 'o'  # Circle marker for P-core points
    ecore_marker = 's'  # Square marker for E-core points

    # Generate a colormap for the frequencies (VF levels)
    vf_colors = plt.cm.viridis(np.linspace(0, 1, len(frequencies)))  # Choose a colormap like 'viridis'
    vf_color_map = {freq: vf_colors[i] for i, freq in enumerate(frequencies)}  # Assign a color for each frequency

    # Loop through each application and plot its corresponding data in a separate subplot
    for app_idx, app_name in enumerate(applications):
        ax = axs[app_idx]
        app_results = results[app_name]

        # Lists to collect all P-core and E-core points across applications
        all_pcore_points = []
        all_ecore_points = []

        # Plot P-core data points (already normalized)
        pcore_data = app_results['P-core']
        for i, (pcore_time, pcore_efficiency) in enumerate(pcore_data):
            freq = frequencies[i]  # Get the corresponding frequency (VF level)
            color = vf_color_map[freq]  # Get the color for this VF level

            # Scatter plot for P-core (same marker, color for frequency)
            ax.scatter(pcore_time, pcore_efficiency, 
                       color=color, marker=pcore_marker, alpha=0.7, label=f"{app_name} (P-core, {freq})")

            # Collect all P-core points for the global hull
            all_pcore_points.append((pcore_time, pcore_efficiency))

        # Plot E-core data points (already normalized)
        ecore_data = app_results['E-core']
        for i, (ecore_time, ecore_efficiency) in enumerate(ecore_data):
            freq = frequencies[i]  # Get the corresponding frequency (VF level)
            color = vf_color_map[freq]  # Get the color for this VF level

            # Scatter plot for E-core (same marker, color for frequency)
            ax.scatter(ecore_time, ecore_efficiency, 
                       color=color, marker=ecore_marker, alpha=0.7, label=f"{app_name} (E-core, {freq})")

            # Collect all E-core points for the global hull
            all_ecore_points.append((ecore_time, ecore_efficiency))

        # Convert lists to NumPy arrays for hull calculation
        all_pcore_points = np.array(all_pcore_points)
        all_ecore_points = np.array(all_ecore_points)

        # Fill rounded convex hull for all P-core points with light blue color
        if len(all_pcore_points) > 2:  # Ensure there are enough points to draw a hull
            fill_rounded_convex_hull(all_pcore_points, ax, '#4E598C', alpha=0.2)

        # Fill rounded convex hull for all E-core points with light red color
        if len(all_ecore_points) > 2:  # Ensure there are enough points to draw a hull
            fill_rounded_convex_hull(all_ecore_points, ax, '#F9C784', alpha=0.2)       
        # Add a title for each subplot corresponding to the application
        ax.set_title(app_name.replace("parsec-","").replace("splash2x.",""), fontweight='bold')


        # Set x-axis and y-axis labels
        if app_idx in [0, 1]:
            ax.set_xticklabels([])  # Remove y ticks

        # Set x-axis and y-axis labels
        if app_idx in [1, 3]:
            ax.set_yticklabels([])  # Remove y ticks

        # Set x-axis and y-axis labels
        if app_idx in [2, 3]:
            ax.set_xlabel('Norm. Execution Time', fontweight='bold')

        # Remove the y-label for rightmost subplots (indices 1 and 3)
        if app_idx in [0, 2]:
            ax.set_ylabel('Norm. Energy Efficiency', fontweight='bold')
        # Set xlim and ylim to have minimum values of 0
        ax.set_xlim(left=0.11, right=1.2)
        ax.set_ylim(bottom=0.301)
        
        # Add grid and other plot aesthetics
        ax.grid(True, which='both', linestyle='--', linewidth=1.2, color='#333', alpha=0.6)
        ax.spines['top'].set_linewidth(1.5)
        ax.spines['right'].set_linewidth(1.5)
        ax.spines['bottom'].set_linewidth(1.5)
        ax.spines['left'].set_linewidth(1.5)


        hull_legend = [
            plt.Line2D([0], [0], color='#4E598C', lw=4, label='P-core Region'),
            plt.Line2D([0], [0], color='#F9C784', lw=4, label='E-core Region')
        ]
        # Add the core type legend (symbols for P-core and E-core)
        #plt.legend(handles=core_legend, loc='lower left', title='Core Type')
        # Combine the legends for core types and convex hulls

        if app_idx == 0:
            ax.legend(handles=hull_legend, loc='upper right')
        elif app_idx == 1:
            ax.legend(handles=hull_legend, loc='lower left')
        elif app_idx == 2:
            ax.legend(handles=hull_legend, loc='upper right')
        elif app_idx == 3:
            ax.legend(handles=hull_legend, loc='lower left')

        # Add a title for each subplot corresponding to the application
        ax.set_title(app_name.replace("parsec-","").replace("splash2x.",""), fontweight='bold')
    # Adjust spacing between subplots
    
    plt.tight_layout(pad=2.0)

    # Save the figure to a file
    plt.savefig(os.path.join(output_dir, "motivational_example_subplots_vf_color_coded.pdf"), dpi=300, format='pdf')
    plt.close()



# Main function to process and plot results for specific applications and frequencies
def main():
    # Define the specific applications to plot
    applications = ['parsec-splash2x.water_nsquared', 'parsec-dedup', 'parsec-splash2x.fft', 'parsec-splash2x.barnes']  # Replace with actual app names
    frequencies = [f"{freq}MHz" for freq in range(1500, 3600, 100)]
    core_types = ["Pcore", "Ecore"]

    output_dir = PAPERPLOT_FOLDER
    os.makedirs(output_dir, exist_ok=True)

    results = {app: {'P-core': [], 'E-core': []} for app in applications}

    for application_name in applications:
        max_efficiency = 0  # Reset max efficiency for each application
        max_time = 0  # Reset max E-core time for each application

        print(f"Processing {application_name}")
        for frequency in frequencies:

            # Step 1: Gather metrics for P-core
            pcore_metrics = gather_metrics(application_name, frequency, "Pcore")
            if pcore_metrics:
                pcore_time, pcore_efficiency = pcore_metrics
                if pcore_time > 0:  # Ensure no division by zero
                    results[application_name]['P-core'].append((pcore_time, pcore_efficiency))
                    max_efficiency = max(max_efficiency, pcore_efficiency)  # Track max efficiency for normalization
                    max_time = max(max_time, pcore_time)  # Track max time for normalization

            # Step 2: Gather metrics for E-core
            ecore_metrics = gather_metrics(application_name, frequency, "Ecore")
            if ecore_metrics:
                ecore_time, ecore_efficiency = ecore_metrics
                if ecore_time > 0:  # Ensure no division by zero
                    results[application_name]['E-core'].append((ecore_time, ecore_efficiency))
                    max_efficiency = max(max_efficiency, ecore_efficiency)  # Track max efficiency for normalization
                    max_time = max(max_time, ecore_time)  # Track max time for normalization

        if max_efficiency == 0:
            print(f"No valid P-core efficiency found for {application_name}, skipping normalization.")
            continue

        if max_time == 0:
            print(f"No valid E-core execution time found for {application_name}, skipping normalization.")
            continue

        # Normalize the data per application
        for i, (time, efficiency) in enumerate(results[application_name]['P-core']):
            normalized_efficiency = normalize_efficiency(efficiency, max_efficiency)
            normalized_time = normalize_execution_time(time, max_time)
            results[application_name]['P-core'][i] = (normalized_time, normalized_efficiency)

        for i, (time, efficiency) in enumerate(results[application_name]['E-core']):
            normalized_efficiency = normalize_efficiency(efficiency, max_efficiency)
            normalized_time = normalize_execution_time(time, max_time)
            results[application_name]['E-core'][i] = (normalized_time, normalized_efficiency)

    # Step 3: Plot the normalized energy efficiency vs normalized execution time for all applications in subplots
    plot_normalized_efficiency_vs_time_with_rounded_subplots(applications, results, output_dir, frequencies)



if __name__ == "__main__":
    main()
