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
    Parse the periodic_counters.log file to extract time and performance counters.
    
    Args:
        file_path (str): Path to the periodic_counters.log file.
        
    Returns:
        pd.DataFrame: A DataFrame containing time and counter data.
    """
    data = {
        'Time (s)': [],
        'Instructions': [],
        'Cache Misses': [],
        'Cache References': []
    }
    pattern = re.compile(r'\[(\d+.\d+)s\] Core \d+: instructions = (\d+) \| cache-misses = (\d+) \| cache-references = (\d+)')
    with open(file_path, 'r') as file:
        for line in file:
            match = pattern.match(line)
            if match:
                time, instructions, cache_misses, cache_references = match.groups()
                data['Time (s)'].append(float(time))
                data['Instructions'].append(int(instructions))
                data['Cache Misses'].append(int(cache_misses))
                data['Cache References'].append(int(cache_references))
    return pd.DataFrame(data)

def plot_periodic_counters(df, output_dir):
    """
    Plot periodic performance counters and save the plots.
    
    Args:
        df (pd.DataFrame): DataFrame containing time and counter data.
        output_dir (str): Directory to save the plots.
    """
    counters = ['Instructions', 'Cache Misses', 'Cache References']
    for counter in counters:
        plt.figure(figsize=(10, 6))
        plt.plot(df['Time (s)'], df[counter], marker='o')
        plt.title(f'{counter} Over Time')
        plt.xlabel('Time (s)')
        plt.ylabel(counter)
        plt.grid(True)
        plt.savefig(os.path.join(output_dir, f'{counter.lower().replace(" ", "_")}_over_time.png'))
        plt.close()

def process_experiment_folders(result_dir):
    """
    Process each experiment folder to generate the necessary plots.

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
                plot_periodic_counters(df_counters, folder_path)


if __name__ == "__main__":
    df_results = gather_results(RESULTS_FOLDER)
    #plot_scaling_behavior_per_application(df_results, RESULTS_FOLDER)
    #process_experiment_folders(RESULTS_FOLDER)
    #plot_scaling_behavior(df_results, RESULTS_FOLDER)
    print(df_results)