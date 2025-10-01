"""
    This is a script to analyze the training folder and generate some statistics about the executed experiments.
    We want to see how the execution time and energy consumption of the target application change with the number of background applications.
"""


import os 
import re
import sys
import matplotlib.pyplot as plt
from scipy.spatial import ConvexHull
import numpy as np
from scipy import stats
from scipy.interpolate import make_interp_spline


import matplotlib.cm as cm

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import ardis.config as config

def parse_execution_log(file_path):
    """Extracts total execution time and energy consumption from execution.log."""
    total_time, total_energy = None, None
    with open(file_path, 'r') as file:
        for line in file:
            if "Total execution time of experiment" in line:
                total_time = float(line.split('=')[1].strip().replace('s', ''))
            elif "Total energy consumed (perf)" in line:
                total_energy = float(line.split('=')[1].strip().replace('Joules', ''))
    return total_time, total_energy

def parse_summary_log(file_path):
    """Extracts the applications and their execution times from summary.log."""
    applications = {}
    with open(file_path, 'r') as file:
        for line in file:
            if line.strip() and not line.startswith("Core"):
                parts = line.strip().split()
                core, app, exec_time = int(parts[0]), parts[1], float(parts[2])
                applications[app] = {'core': core, 'execution_time': exec_time}
    return applications

def parse_periodic_counters(file_path, applications):
    """Extracts the mapping sequence, migration counts, and timestamps for each application."""
    mappings = {app: {
        'sequence': '', 
        'migrations': 0, 
        'p_core_migrations': 0, 
        'e_core_migrations': 0,
        'time_on_each_core': [],
    } for app in applications}
    
    last_mapping = {}
    last_timestamp = {}
    time_on_cores = {}
    
    with open(file_path, 'r') as file:
        for line in file:
            timestamp_match = re.match(r"\[(\d+\.\d+)s\]", line)
            if timestamp_match:
                current_timestamp = float(timestamp_match.group(1))
            
            if "Core" in line and "app =" in line:
                core_match = re.match(r"\[(\d+\.\d+)s\] Core (\d+): app = (\S+)", line)
                if core_match:
                    core = int(core_match.group(2))
                    app = core_match.group(3)
                    
                    if app in mappings:
                        core_type = 'P' if core in config.intel_p_core_ids else 'E'
                        mappings[app]['sequence'] += core_type + str(core)

                        if app in last_mapping and last_mapping[app] != core:
                            mappings[app]['migrations'] += 1
                            if core_type == 'P':
                                mappings[app]['p_core_migrations'] += 1
                            else:
                                mappings[app]['e_core_migrations'] += 1
                            
                            time_spent = current_timestamp - last_timestamp[app]
                            mappings[app]['time_on_each_core'].append({
                                'core_type': 'P' if last_mapping[app] in config.intel_p_core_ids else 'E',
                                'core': last_mapping[app],
                                'time_spent': time_spent
                            })
                        
                        last_mapping[app] = core
                        last_timestamp[app] = current_timestamp
                        
            if "Migration Executed" in line:
                for app, core in last_mapping.items():
                    if app in mappings:
                        core_type = 'P' if core in config.intel_p_core_ids else 'E'
                        mappings[app]['sequence'] += core_type
                        mappings[app]['migrations'] += 1
                        if core_type == 'P':
                            mappings[app]['p_core_migrations'] += 1
                        else:
                            mappings[app]['e_core_migrations'] += 1
                        time_spent = current_timestamp - last_timestamp.get(app, 0)
                        mappings[app]['time_on_each_core'].append({
                            'core_type': core_type,
                            'core': core,
                            'time_spent': time_spent
                        })
    return mappings

def analyze_experiment(result_folder):
    """Main function to analyze a single experiment folder."""
    execution_log_path = os.path.join(result_folder, 'execution.log')
    summary_log_path = os.path.join(result_folder, 'summary.log')
    periodic_counters_log_path = os.path.join(result_folder, 'periodic_counters.log')

    total_time, total_energy = parse_execution_log(execution_log_path)
    applications = parse_summary_log(summary_log_path)
    mappings = parse_periodic_counters(periodic_counters_log_path, applications)

    experiment_summary = {
        'total_time': total_time,
        'total_energy': total_energy,
        'applications': applications,
        'mappings': mappings
    }
    return experiment_summary

def calculate_core_usage_percentages(sequence):
    """Calculate percentage time spent on P-cores vs E-cores from the mapping sequence."""
    p_cores = sequence.count('P')
    e_cores = sequence.count('E')
    total = p_cores + e_cores
    return (p_cores / total) * 100 if total else 0, (e_cores / total) * 100 if total else 0

def analyze_application_across_experiments(application_name, results_folder):
    """Analyze results for a specific application across multiple experiments."""
    execution_times = []
    p_core_times = []
    num_applications = []  # New list to store the number of applications

    for root, dirs, files in os.walk(results_folder):
        #if "_nomig" in root:
        if 'summary.log' in files and 'periodic_counters.log' in files:
            summary_path = os.path.join(root, 'summary.log')
            summary_data = parse_summary_log(summary_path)

            if application_name in summary_data:
                # Get execution time for the application
                execution_time = summary_data[application_name]['execution_time']
                # Get the number of applications in this experiment
                num_apps = len(summary_data)
                
                # Parse periodic_counters.log for core mappings
                periodic_path = os.path.join(root, 'periodic_counters.log')
                mappings = parse_periodic_counters(periodic_path, summary_data)
                
                # Calculate the P-core time percentage
                app_mapping_data = mappings[application_name]
                p_time, _ = calculate_core_usage_percentages(app_mapping_data['sequence'])
                
                # Append data to lists
                execution_times.append(execution_time)
                p_core_times.append(p_time)
                num_applications.append(num_apps)  # Append the count of applications

    # Call the plotting function with the additional num_applications list
    plot_execution_times_with_bounds(application_name, execution_times, p_core_times, num_applications)


def plot_execution_times(application_name, execution_times, p_core_times, e_core_times):
    """Generates a scatter plot for execution times with core usage annotations."""
    plt.figure(figsize=(10, 6))
    colors = [(p / 100, 0, e / 100) for p, e in zip(p_core_times, e_core_times)]
    
    for idx, (exec_time, p_time, e_time, color) in enumerate(zip(execution_times, p_core_times, e_core_times, colors)):
        plt.scatter(idx, exec_time, color=color, s=50, edgecolor='black')
        plt.annotate(f"{p_time:.1f}% P, {e_time:.1f}% E", (idx, exec_time), textcoords="offset points", xytext=(5, 5), ha='center', fontsize=8)

    plt.xlabel('Experiment')
    plt.ylabel('Execution Time (s)')
    plt.title(f'Execution Time Analysis for {application_name}')
    plt.grid(True)
    plt.savefig(os.path.join(config.PLOTS_FOLDER, f"analysis_{application_name}.png"))

def plot_execution_times_with_bounds(application_name, execution_times, p_core_times, num_applications):
    """
    Plots execution times as a scatter plot with a bounded colored area.
    The scatter points are colored based on the percentage of time spent on P-cores,
    and the y-axis represents the number of applications in each experiment.
    
    Parameters:
        application_name (str): Name of the application being analyzed.
        execution_times (list): List of observed execution times for each experiment.
        p_core_times (list): List of percentage times spent on P-cores for each experiment.
        num_applications (list): Number of applications in each experiment.
    """
    plt.figure(figsize=(10, 6))

    # Scatter plot with color scale based on P-core time percentage and y-axis as number of applications
    scatter = plt.scatter(
        num_applications,  # Y-axis now represents the number of applications
        execution_times, 
        s=30,  # Slightly increased dot size
        c=p_core_times,  # Color based on percentage time on P-cores
        cmap="coolwarm",  # Color map from blue (low) to red (high)
        label="Execution Time"
    )

    # Create a bounded area using a convex hull around the points
    points = np.column_stack((num_applications, execution_times))
    if len(points) > 2:  # ConvexHull requires at least three points
        hull = ConvexHull(points)
        # Plot the filled area
        plt.fill(points[hull.vertices, 0], points[hull.vertices, 1], 'skyblue', alpha=0.3, edgecolor='none', label="Bounded Area")

    # Add color bar legend for P-core time percentage
    cbar = plt.colorbar(scatter)
    cbar.set_label("Percentage Time on P-cores (%)")

    # Plot setup
    plt.ylabel("Execution Time (seconds)")
    plt.xlabel("Number of Background Applications")
    plt.title(f"Execution Times with Bounded Area for {application_name}")
    plt.legend()
    plt.savefig(os.path.join(config.PLOTS_FOLDER, f"analysis_{application_name}.png"))


def plot_overall_experiment_insights(results_folder):
    """
    Generate a multi-application plot showing execution time variation, core usage, and background application count.
    """
    # Collect data for each application across experiments
    app_data = {}
    for application_name in config.parsec_apps:
        execution_times = []
        p_core_times = []
        num_applications = []
        
        for root, dirs, files in os.walk(results_folder):
            if 'summary.log' in files and 'periodic_counters.log' in files:
                summary_path = os.path.join(root, 'summary.log')
                summary_data = parse_summary_log(summary_path)
                
                if application_name in summary_data:
                    # Get execution time and background application count
                    execution_time = summary_data[application_name]['execution_time']
                    num_apps = len(summary_data)
                    
                    # Parse periodic_counters.log for core usage percentages
                    periodic_path = os.path.join(root, 'periodic_counters.log')
                    mappings = parse_periodic_counters(periodic_path, summary_data)
                    app_mapping_data = mappings[application_name]
                    p_time, _ = calculate_core_usage_percentages(app_mapping_data['sequence'])
                    
                    # Store data for the current application
                    execution_times.append(execution_time)
                    p_core_times.append(p_time)
                    num_applications.append(num_apps)
        
        # Store in dictionary for plotting
        if execution_times:
            app_data[application_name] = {
                'execution_times': execution_times,
                'p_core_times': p_core_times,
                'num_applications': num_applications
            }

    # Create the figure with subplots for each application
    num_apps = len(app_data)
    fig, axs = plt.subplots(nrows=(num_apps // 3) + 1, ncols=3, figsize=(18, 5 * ((num_apps // 3) + 1)))
    fig.suptitle("Execution Time and Core Usage Insights Across Applications", fontsize=16)
    axs = axs.flatten()

    # Generate scatter plots for each application
    for idx, (app_name, data) in enumerate(app_data.items()):
        ax = axs[idx]
        scatter = ax.scatter(
            data['execution_times'], 
            data['p_core_times'],
            c=data['num_applications'],
            cmap="viridis",
            s=40,
            edgecolor='k',
            alpha=0.7
        )
        
        ax.set_title(app_name)
        ax.set_xlabel("Execution Time (seconds)")
        ax.set_ylabel("P-Core Usage (%)")
        ax.grid(True)

    # Add colorbar for number of applications
    cbar = fig.colorbar(scatter, ax=axs, orientation="horizontal", pad=0.1)
    cbar.set_label("Number of Background Applications")

    # Adjust layout and save the figure
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(os.path.join(config.PLOTS_FOLDER, "overall_application_insights.png"))


def find_counterintuitive_examples(application_name, results_folder):
    """
    Identify and plot counterintuitive examples where E-core execution times outperform P-core execution times
    as the number of background applications increases.

    Parameters:
        application_name (str): Name of the application being analyzed.
        results_folder (str): Path to the folder containing experiment data.
    """
    execution_times_p = {}
    execution_times_e = {}

    # Iterate through experiments to collect execution times
    for root, dirs, files in os.walk(results_folder):
        #if "_nomig_" in root:
        if 'summary.log' in files and 'periodic_counters.log' in files:
            summary_path = os.path.join(root, 'summary.log')
            summary_data = parse_summary_log(summary_path)

            if application_name in summary_data:
                execution_time = summary_data[application_name]['execution_time']
                periodic_path = os.path.join(root, 'periodic_counters.log')
                mappings = parse_periodic_counters(periodic_path, summary_data)
                app_mapping_data = mappings[application_name]
                
                # Count background applications in this experiment
                num_bg_apps = len(summary_data) - 1

                # Determine core type (100% P-core or 0% P-core)
                p_time, _ = calculate_core_usage_percentages(app_mapping_data['sequence'])
                core_type = "P" if p_time == 100 else "E"

                # Store execution time based on core type
                if core_type == "P":
                    if num_bg_apps not in execution_times_p:
                        execution_times_p[num_bg_apps] = []
                    execution_times_p[num_bg_apps].append(execution_time)
                else:
                    if num_bg_apps not in execution_times_e:
                        execution_times_e[num_bg_apps] = []
                    execution_times_e[num_bg_apps].append(execution_time)

    # Identify counterintuitive examples and plot them
    plot_counterintuitive_examples(application_name, execution_times_p, execution_times_e)


def plot_counterintuitive_examples(application_name, execution_times_p, execution_times_e):
    """
    Plot discrete execution times for P-cores and E-cores with highlights on counterintuitive examples.

    Parameters:
        application_name (str): Name of the application being analyzed.
        execution_times_p (dict): Execution times on P-cores for varying background applications.
        execution_times_e (dict): Execution times on E-cores for varying background applications.
    """
    sorted_bg_apps = sorted(set(execution_times_p.keys()).union(execution_times_e.keys()))
    median_times_p = [np.max(execution_times_p[bg]) if bg in execution_times_p else None for bg in sorted_bg_apps]
    median_times_e = [np.min(execution_times_e[bg]) if bg in execution_times_e else None for bg in sorted_bg_apps]

    # Identify crossover points (counterintuitive examples)
    counterintuitive_points = [
        (bg, median_times_e[idx], median_times_p[idx])
        for idx, bg in enumerate(sorted_bg_apps)
        if median_times_p[idx] is not None and median_times_e[idx] is not None and median_times_e[idx] < median_times_p[idx]
    ]

    # Plotting
    plt.figure(figsize=(10, 6))
    plt.plot(sorted_bg_apps, median_times_p, 'bo-', label="100% P-core Time", markersize=6)
    plt.plot(sorted_bg_apps, median_times_e, 'r--', label="0% P-core Time", markersize=6)

    # Highlight counterintuitive points
    for bg, e_time, p_time in counterintuitive_points:
        plt.scatter(bg, e_time, color='green', edgecolor='black', s=80, zorder=5, label="Counterintuitive Point" if bg == counterintuitive_points[0][0] else "")
        plt.annotate(f"BG: {bg}\nE:{e_time:.2f} < P:{p_time:.2f}", (bg, e_time), textcoords="offset points", xytext=(5,5), ha='center')

    # Final plot adjustments
    plt.xlabel("Number of Background Applications")
    plt.ylabel("Median Execution Time (s)")
    plt.title(f"Counterintuitive Execution Time Trends for {application_name}")
    plt.legend()
    plt.grid(True)
    plt.savefig(os.path.join(config.PLOTS_FOLDER, f"counterintuitive_{application_name}.png"))
    plt.show()



def main():
    result_folder = config.TRAINING_RESULTS_FOLDER
    # Generate individual plots for each application to show the performance scaling behavior
    for application_name in config.parsec_apps:
        analyze_application_across_experiments(application_name, result_folder)

    #for app in config.parsec_apps:
    #    find_counterintuitive_examples(app, result_folder)

# Entry point for the script
if __name__ == "__main__":
    main()
