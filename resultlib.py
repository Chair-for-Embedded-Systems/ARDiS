from config import *
import os
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
import re

def parse_summary_log(file_path):
    """
    Parse the summary.log file to extract application name and execution time.
    
    Args:
        file_path (str): Path to the summary.log file.
        
    Returns:
        dict: A dictionary with 'Application' and 'Execution time (s)'.
    """
    with open(file_path, 'r') as file:
        lines = file.readlines()
        data = lines[1].strip().split('\t')  # Assuming the data is in the second line
        return {
            'Core': data[0],
            'Application': data[1],
            'Execution time (s)': float(data[2])
        }

def extract_core_info(folder_name):
    """
    Extract core type and frequency from the folder name.
    
    Args:
        folder_name (str): Name of the folder.
        
    Returns:
        tuple: A tuple containing core type ('Ecore' or 'Pcore') and frequency.
    """
    parts = folder_name.split('_')
    core_type = parts[-1]
    frequency = parts[-2]
    return core_type, frequency

def gather_results(result_dir):
    """
    Gather results from all experiment folders and display a table.
    
    Args:
        result_dir (str): Path to the results directory.
        
    Returns:
        pd.DataFrame: A DataFrame containing the execution times for each application.
    """
    results = []
    for folder in os.listdir(result_dir):
        folder_path = os.path.join(result_dir, folder)
        if os.path.isdir(folder_path):
            summary_log_path = os.path.join(folder_path, 'summary.log')
            if os.path.exists(summary_log_path):
                summary_data = parse_summary_log(summary_log_path)
                core_type, frequency = extract_core_info(folder)
                summary_data['Core Type'] = core_type
                summary_data['Frequency'] = frequency
                results.append(summary_data)
    
    df = pd.DataFrame(results)
    df_pivot = df.pivot_table(index='Application', columns=['Core Type', 'Frequency'], values='Execution time (s)')
    return df_pivot

def plot_scaling_behavior(df, output_dir):
    """
    Plot the scaling behavior of applications on E cores and P cores.
    
    Args:
        df (pd.DataFrame): DataFrame containing execution times, with VF levels and core types.
        output_dir (str): Directory to save the plots.
    """
    # Separate data for E cores and P cores
    ecore_data = df['Ecore']
    pcore_data = df['Pcore']
    
    # Define plot style
    plt.style.use('default')  # Use default style

    # Plot for E cores
    plt.figure(figsize=(10, 6))
    for app in ecore_data.index:
        plt.plot(ecore_data.columns, ecore_data.loc[app], marker='o', label=app)
    plt.title('Scaling Behavior on E Cores')
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('Execution Time (s)')
    plt.legend(loc='upper right')
    plt.grid(True)
    plt.savefig(f"{output_dir}/scaling_behavior_E_cores.png")
    plt.show()

    # Plot for P cores
    plt.figure(figsize=(10, 6))
    for app in pcore_data.index:
        plt.plot(pcore_data.columns, pcore_data.loc[app], marker='o', label=app)
    plt.title('Scaling Behavior on P Cores')
    plt.xlabel('Frequency (MHz)')
    plt.ylabel('Execution Time (s)')
    plt.legend(loc='upper right')
    plt.grid(True)
    plt.savefig(f"{output_dir}/scaling_behavior_P_cores.png")
    plt.show()

def calculate_percentage_differences(ecore_times, pcore_times):
    """
    Calculate the percentage differences between E cores and P cores execution times.

    Args:
        ecore_times (pd.Series): Execution times on E cores.
        pcore_times (pd.Series): Execution times on P cores.

    Returns:
        list: List of percentage differences for each frequency.
    """
    differences = []
    for e_time, p_time in zip(ecore_times, pcore_times):
        if e_time and p_time:
            diff = ((p_time - e_time) / e_time) * 100
            differences.append(diff)
    return differences

def plot_scaling_behavior_per_application(df, output_dir):
    """
    Plot the scaling behavior of each application on E cores and P cores, with annotations.

    Args:
        df (pd.DataFrame): DataFrame containing execution times, with VF levels and core types.
        output_dir (str): Directory to save the plots.
    """
    # Extract core data for E cores and P cores
    ecore_data = df['Ecore']
    pcore_data = df['Pcore']
    
    # Define plot style
    plt.style.use('default')  # Use default style
    
    # Plot for each application
    for app in ecore_data.index:
        plt.figure(figsize=(12, 8))
        ecore_times = ecore_data.loc[app]
        pcore_times = pcore_data.loc[app]

        if app in ecore_data.index:
            plt.plot(ecore_data.columns, ecore_data.loc[app], marker='o', label='E Cores', color='blue')
        if app in pcore_data.index:
            plt.plot(pcore_data.columns, pcore_data.loc[app], marker='s', label='P Cores', color='green')

        # Calculate percentage differences
        differences = calculate_percentage_differences(ecore_times, pcore_times)
        if differences:
            max_diff = max(differences)
            min_diff = min(differences)
            avg_diff = sum(differences) / len(differences)

            # Annotate percentage differences
            for freq, diff in zip(ecore_data.columns, differences):
                plt.text(freq, pcore_times[freq], f"{diff:.2f}%", fontsize=12, ha='right')
                # Highlight max and min differences
                if diff == max_diff:
                    plt.plot(freq, pcore_times[freq], marker='^', color='red', markersize=10, label='Max Difference')
                if diff == min_diff:
                    plt.plot(freq, pcore_times[freq], marker='v', color='purple', markersize=10, label='Min Difference')

            plt.title(f'Scaling Behavior for {app} (Mean Diff {avg_diff:.2f}%)')
        else:
            plt.title(f'Scaling Behavior for {app}')
        
        plt.xlabel('Frequency (MHz)', fontsize=14)
        plt.ylabel('Execution Time (s)', fontsize=14)
        plt.legend(loc='upper right')
        plt.grid(True)
        plt.savefig(f"{output_dir}/scaling_behavior_{app}.png")
        plt.show()

def parse_periodic_counters(file_path):
    """
    Parse the periodic_counters.log file to extract time, performance counters, and energy data.

    Args:
        file_path (str): Path to the periodic_counters.log file.

    Returns:
        pd.DataFrame: A DataFrame containing time, performance counters, and energy data.
    """
    data = {
        'Time (s)': [],
        'Instructions': [],
        'Cache Misses': [],
        'Cache References': [],
        'LLC Loads': [],
        'LLC Load Misses': [],
        'LLC Stores': [],
        'LLC Store Misses': [],
        'Energy Package (uJ)': [],
        'Energy Cores (uJ)': [],
        'Energy PSYS (uJ)': []
    }

    pattern = re.compile(
        r'\[(\d+\.\d+)s\] Core \d+: instructions = (\d+) \| cache-misses = (\d+) \| cache-references = (\d+) '
        r'\| LLC-loads = (\d+) \| LLC-load-misses = (\d+) \| LLC-stores = (\d+) \| LLC-store-misses = (\d+) '
        r'\| power/energy-pkg/ = (\d+) \| power/energy-cores/ = (\d+) \| power/energy-psys/ = (\d+)'
    )

    with open(file_path, 'r') as file:
        for line in file:
            match = pattern.match(line)
            if match:
                time, instructions, cache_misses, cache_references, llc_loads, llc_load_misses, llc_stores, llc_store_misses, energy_pkg, energy_cores, energy_psys = match.groups()
                data['Time (s)'].append(float(time))
                data['Instructions'].append(int(instructions))
                data['Cache Misses'].append(int(cache_misses))
                data['Cache References'].append(int(cache_references))
                data['LLC Loads'].append(int(llc_loads))
                data['LLC Load Misses'].append(int(llc_load_misses))
                data['LLC Stores'].append(int(llc_stores))
                data['LLC Store Misses'].append(int(llc_store_misses))
                data['Energy Package (uJ)'].append(int(energy_pkg))
                data['Energy Cores (uJ)'].append(int(energy_cores))
                data['Energy PSYS (uJ)'].append(int(energy_psys))

    return pd.DataFrame(data)

def calculate_energy_metrics(df):
    """
    Calculate energy consumption and energy efficiency.

    Args:
        df (pd.DataFrame): DataFrame containing time, energy, and instruction data.
    
    Returns:
        pd.DataFrame: A DataFrame with additional columns for energy and efficiency metrics.
        dict: A dictionary with total energy and efficiency metrics.
    """
    df['Energy (J)'] = df['Energy Package (uJ)'] / 1e6  # Convert to Joules
    df['Energy Efficiency (Instructions/J)'] = df['Instructions'] / df['Energy (J)']
    
    total_energy = df['Energy (J)'].sum()
    total_instructions = df['Instructions'].sum()
    overall_efficiency = total_instructions / total_energy if total_energy > 0 else 0
    
    energy_metrics = {
        'Total Energy (J)': total_energy,
        'Total Instructions': total_instructions,
        'Overall Efficiency (Instructions/J)': overall_efficiency
    }
    
    return df, energy_metrics

def plot_energy_metrics(df, energy_metrics, output_dir, core_type):
    """
    Plot energy consumption and efficiency over time.

    Args:
        df (pd.DataFrame): DataFrame containing time, energy, and efficiency data.
        energy_metrics (dict): Dictionary containing total energy and efficiency metrics.
        output_dir (str): Directory to save the plots.
        core_type (str): The type of core being plotted ('E-core' or 'P-core').
    """
    total_energy = energy_metrics['Total Energy (J)']
    overall_efficiency = energy_metrics['Overall Efficiency (Instructions/J)']

    # Plot energy consumption over time
    plt.figure(figsize=(10, 6))
    plt.plot(df['Time (s)'], df['Energy (J)'], marker='o')
    plt.title(f'{core_type} Energy Consumption Over Time\nTotal: {total_energy:.2f} J')
    plt.xlabel('Time (s)')
    plt.ylabel('Energy (J)')
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, f'{core_type}_energy_consumption_over_time.png'))
    plt.close()

    # Plot energy efficiency over time
    plt.figure(figsize=(10, 6))
    plt.plot(df['Time (s)'], df['Energy Efficiency (Instructions/J)'], marker='o')
    plt.title(f'{core_type} Energy Efficiency Over Time\nOverall Efficiency: {overall_efficiency:.2f} Instructions/J')
    plt.xlabel('Time (s)')
    plt.ylabel('Energy Efficiency (Instructions/J)')
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, f'{core_type}_energy_efficiency_over_time.png'))
    plt.close()

def process_experiment_folders(result_dir):
    """
    Process each experiment folder to generate the necessary plots, including energy metrics.

    Args:
        result_dir (str): Path to the results directory.
    """
    for folder in os.listdir(result_dir):
        folder_path = os.path.join(result_dir, folder)
        print(f"Processing folder: {folder}")
        if os.path.isdir(folder_path):
            # Parse periodic_counters.log and generate periodic counters plots
            periodic_counters_path = os.path.join(folder_path, 'periodic_counters.log')
            if os.path.exists(periodic_counters_path):
                df_counters = parse_periodic_counters(periodic_counters_path)
                df_counters, energy_metrics = calculate_energy_metrics(df_counters)
                plot_periodic_counters(df_counters, folder_path)
                core_type = extract_core_info(folder)[0]
                plot_energy_metrics(df_counters, energy_metrics, folder_path, core_type)

def plot_periodic_counters(df, output_dir):
    """
    Plot the periodic counters over time as subplots.

    Args:
        df (pd.DataFrame): DataFrame containing time, energy, and performance data.
        output_dir (str): Directory to save the plots.
    """
    # Define plot style
    plt.style.use('default')  # Use default style

    # Create a figure with subplots
    fig, axs = plt.subplots(9, 1, figsize=(12, 36), sharex=True)

    # Plot instructions over time
    axs[0].plot(df['Time (s)'], df['Instructions'], marker='o', label='Instructions')
    axs[0].set_title('Instructions Over Time')
    axs[0].set_ylabel('Instructions')
    axs[0].grid(True)

    # Plot cache misses over time
    axs[1].plot(df['Time (s)'], df['Cache Misses'], marker='s', color='orange', label='Cache Misses')
    axs[1].set_title('Cache Misses Over Time')
    axs[1].set_ylabel('Cache Misses')
    axs[1].grid(True)

    # Plot cache references over time
    axs[2].plot(df['Time (s)'], df['Cache References'], marker='^', color='green', label='Cache References')
    axs[2].set_title('Cache References Over Time')
    axs[2].set_ylabel('Cache References')
    axs[2].grid(True)

    # Plot LLC loads over time
    axs[3].plot(df['Time (s)'], df['LLC Loads'], marker='o', color='blue', label='LLC Loads')
    axs[3].set_title('LLC Loads Over Time')
    axs[3].set_ylabel('LLC Loads')
    axs[3].grid(True)

    # Plot LLC load misses over time
    axs[4].plot(df['Time (s)'], df['LLC Load Misses'], marker='s', color='purple', label='LLC Load Misses')
    axs[4].set_title('LLC Load Misses Over Time')
    axs[4].set_ylabel('LLC Load Misses')
    axs[4].grid(True)

    # Plot LLC stores over time
    axs[5].plot(df['Time (s)'], df['LLC Stores'], marker='^', color='brown', label='LLC Stores')
    axs[5].set_title('LLC Stores Over Time')
    axs[5].set_ylabel('LLC Stores')
    axs[5].grid(True)

    # Plot LLC store misses over time
    axs[6].plot(df['Time (s)'], df['LLC Store Misses'], marker='d', color='cyan', label='LLC Store Misses')
    axs[6].set_title('LLC Store Misses Over Time')
    axs[6].set_ylabel('LLC Store Misses')
    axs[6].grid(True)

    # Plot energy package over time
    axs[7].plot(df['Time (s)'], df['Energy Package (uJ)'], marker='o', color='red', label='Energy Package')
    axs[7].set_title('Energy Package Over Time')
    axs[7].set_ylabel('Energy (uJ)')
    axs[7].grid(True)

    # Plot energy cores and PSYS over time
    axs[8].plot(df['Time (s)'], df['Energy Cores (uJ)'], marker='s', color='magenta', label='Energy Cores')
    axs[8].plot(df['Time (s)'], df['Energy PSYS (uJ)'], marker='^', color='yellow', label='Energy PSYS')
    axs[8].set_title('Energy Cores and PSYS Over Time')
    axs[8].set_xlabel('Time (s)')
    axs[8].set_ylabel('Energy (uJ)')
    axs[8].legend(loc='upper right')
    axs[8].grid(True)

    # Adjust layout and save the figure
    plt.tight_layout()
    plt.savefig(os.path.join(output_dir, 'periodic_counters_and_energy_metrics_over_time.png'))
    plt.close()


def compare_instructions_for_app(result_dir, app_name, frequency):
    """
    Compare the total instructions executed on E-core and P-core for a given application and frequency.

    Args:
        result_dir (str): Path to the results directory.
        app_name (str): Name of the application.
        frequency (str): Frequency at which the application was executed (e.g., '1500MHz').

    Returns:
        dict: A dictionary showing the difference in instructions executed between E-core and P-core.
    """
    core_instruction_data = {}

    # Initialize variables to store folder names
    ecore_folder = None
    pcore_folder = None

    for folder in os.listdir(result_dir):
        if app_name in folder and frequency in folder:
            if 'Ecore' in folder:
                ecore_folder = folder
            elif 'Pcore' in folder:
                pcore_folder = folder

    if not ecore_folder or not pcore_folder:
        raise FileNotFoundError("Could not find both E-core and P-core result folders for the specified app and frequency.")

    # Extract instructions for E-core
    ecore_path = os.path.join(result_dir, ecore_folder, 'periodic_counters.log')
    if os.path.exists(ecore_path):
        _, e_core_instructions = parse_periodic_counters(ecore_path)
        core_instruction_data['E-core'] = e_core_instructions
    else:
        raise FileNotFoundError(f"periodic_counters.log not found in {ecore_folder}")

    # Extract instructions for P-core
    pcore_path = os.path.join(result_dir, pcore_folder, 'periodic_counters.log')
    if os.path.exists(pcore_path):
        _, p_core_instructions = parse_periodic_counters(pcore_path)
        core_instruction_data['P-core'] = p_core_instructions
    else:
        raise FileNotFoundError(f"periodic_counters.log not found in {pcore_folder}")

    # Compare total instructions between E-core and P-core
    instruction_comparison = {
        'E-core Instructions': f"{core_instruction_data['E-core']:.2e}",
        'P-core Instructions': f"{core_instruction_data['P-core']:.2e}",
        'Instruction Difference': f"{abs(core_instruction_data['P-core'] - core_instruction_data['E-core']):.2e}",
        'Match': core_instruction_data['E-core'] == core_instruction_data['P-core']
    }
    
    return instruction_comparison

def compare_energy_and_efficiency(result_dir, available_apps, frequency):
    """
    Compare the total energy consumption and energy efficiency for applications on E-core and P-core.

    Args:
        result_dir (str): Path to the results directory.
        available_apps (list): List of application names.
        frequency (str): Frequency at which the applications were executed (e.g., '1500MHz').

    Returns:
        pd.DataFrame: A DataFrame containing the comparison results.
    """
    comparison_data = {
        'Application': [],
        'Core Type': [],
        'Total Energy (J)': [],
        'Overall Efficiency (Instructions/J)': []
    }

    for app_name in available_apps:
        ecore_folder, pcore_folder = None, None
        for folder in os.listdir(result_dir):
            if app_name in folder and frequency in folder:
                if 'Ecore' in folder:
                    ecore_folder = folder
                elif 'Pcore' in folder:
                    pcore_folder = folder

        if not ecore_folder or not pcore_folder:
            print(f"Skipping {app_name} at {frequency}: Folders not found for both cores.")
            continue

        for core_type, folder in zip(['E-core', 'P-core'], [ecore_folder, pcore_folder]):
            periodic_counters_path = os.path.join(result_dir, folder, 'periodic_counters.log')
            if os.path.exists(periodic_counters_path):
                df_counters = parse_periodic_counters(periodic_counters_path)
                _, energy_metrics = calculate_energy_metrics(df_counters)
                comparison_data['Application'].append(app_name.replace('spec-', ''))
                comparison_data['Core Type'].append(core_type)
                comparison_data['Total Energy (J)'].append(energy_metrics['Total Energy (J)'])
                comparison_data['Overall Efficiency (Instructions/J)'].append(energy_metrics['Overall Efficiency (Instructions/J)'])

    return pd.DataFrame(comparison_data)

def plot_energy_comparison(df_comparison, output_dir, frequency):
    """
    Plot the comparison of energy consumption and efficiency for each application at a given frequency.

    Args:
        df_comparison (pd.DataFrame): DataFrame containing comparison data for each application.
        output_dir (str): Directory to save the plots.
        frequency (str): The frequency for which the plots are generated.
    """
    apps = df_comparison['Application'].unique()

    # Plot total energy comparison
    plt.figure(figsize=(12, 8))
    for app in apps:
        data = df_comparison[df_comparison['Application'] == app]
        plt.bar(f"{app}-E", data[data['Core Type'] == 'E-core']['Total Energy (J)'], label=f'{app} E-core')
        plt.bar(f"{app}-P", data[data['Core Type'] == 'P-core']['Total Energy (J)'], label=f'{app} P-core')
    plt.title(f'Total Energy Consumption Comparison at {frequency}')
    plt.ylabel('Total Energy (J)')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, f'total_energy_comparison_{frequency}.png'))
    plt.close()

    # Plot energy efficiency comparison
    plt.figure(figsize=(12, 8))
    for app in apps:
        data = df_comparison[df_comparison['Application'] == app]
        plt.bar(f"{app}-E", data[data['Core Type'] == 'E-core']['Overall Efficiency (Instructions/J)'], label=f'{app} E-core')
        plt.bar(f"{app}-P", data[data['Core Type'] == 'P-core']['Overall Efficiency (Instructions/J)'], label=f'{app} P-core')
    plt.title(f'Energy Efficiency Comparison at {frequency}')
    plt.ylabel('Overall Efficiency (Instructions/J)')
    plt.xticks(rotation=45)
    plt.grid(True)
    plt.savefig(os.path.join(output_dir, f'energy_efficiency_comparison_{frequency}.png'))
    plt.close()

def sanity_instruction_count_same_app(result_dir, available_apps, frequencies):
    """
    Perform a sanity check on the instruction counts for each application across different frequencies.

    Args:
        result_dir (str): Path to the results directory.
        available_apps (list): List of application names.
        frequencies (list): List of frequencies to check.
    """
    for app in available_apps:
        print(f"\n############ Comparing instructions for {app}...")
        for frequency in frequencies:
            comparison_result = compare_instructions_for_app(result_dir, app, frequency)
            print(f"Instruction Comparison for {app} at {frequency}:")
            for key, value in comparison_result.items():
                print(f"{key}: {value}")

if __name__ == "__main__":
    #df_results = gather_results(RESULTS_FOLDER)
    #print(df_results)
    # Example to process experiment folders and plot results
    process_experiment_folders(RESULTS_FOLDER)

    # Example to compare energy and efficiency across applications
    #frequencies = ['1500MHz', '1000MHz']  # Example frequencies
    #for freq in frequencies:
    #    df_comparison = compare_energy_and_efficiency(RESULTS_FOLDER, available_apps, freq)
    #    plot_energy_comparison(df_comparison, RESULTS_FOLDER, freq)
