import os
import re
import glob
import sys
import numpy as np

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))
import ardis.config as config

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
                energy = int(energy_match.group(1))

                cumulative_instr += instructions
                cumulative_energy_value += energy

                time_points.append(time)
                cumulative_instructions.append(cumulative_instr)
                cumulative_energy.append(cumulative_energy_value)
    
    return time_points, cumulative_instructions, cumulative_energy

# Function to generate the LaTeX table
def generate_latex_table(energy_type, frequency):
    rows = []
    rows.append(r"\begin{table*}[h!]")
    rows.append(r"\centering")
    rows.append(r"\begin{tabular}{|l|ccc|ccc|ccc|}")
    rows.append(r"\hline")
    rows.append(r"\textbf{Application} & \multicolumn{3}{c|}{\textbf{E-cores}} & \multicolumn{3}{c|}{\textbf{P-cores}} & \textbf{Total} & \textbf{P-core} & \textbf{E-core} \\")
    rows.append(r" & \textbf{Time (s)} & \textbf{Energy (J)} & \textbf{Efficiency} & \textbf{Time (s)} & \textbf{Energy (J)} & \textbf{Efficiency} & \textbf{MInstr} & \textbf{Faster} & \textbf{More Efficient} \\")
    rows.append(r" & & & \textbf{(MInstr/J)} & & & \textbf{(MInstr/J)} & & \textbf{(\%)} & \textbf{(\%)} \\")
    rows.append(r"\hline")

    log_directory = config.RESULTS_FOLDER

    for application_name in config.available_apps:
        # Use glob to find the directories matching the application name for P-core and E-core at the specified frequency
        pcore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Pcore"))
        ecore_dirs = glob.glob(os.path.join(log_directory, f"*_{application_name}_{frequency}_Ecore"))

        if not (pcore_dirs and ecore_dirs):
            continue

        # Take the first matching directory (assuming there's only one result per application)
        pcore_file = os.path.join(pcore_dirs[0], "periodic_counters.log")
        ecore_file = os.path.join(ecore_dirs[0], "periodic_counters.log")

        # Parse the logs
        ecore_time, ecore_instr, ecore_energy = parse_log_file(ecore_file, energy_type)
        pcore_time, pcore_instr, pcore_energy = parse_log_file(pcore_file, energy_type)

        # Calculate metrics for E-core
        ecore_total_time = ecore_time[-1]
        ecore_total_energy = ecore_energy[-1]
        ecore_total_instructions = ecore_instr[-1]

        # Calculate metrics for P-core
        pcore_total_time = pcore_time[-1]
        pcore_total_energy = pcore_energy[-1]
        pcore_total_instructions = pcore_instr[-1]

        # Calculate the average number of instructions executed
        avg_instructions = (ecore_total_instructions + pcore_total_instructions) / 2
        avg_millions_instr = avg_instructions / 1e6

        # Recalculate energy efficiency using the average instructions
        ecore_efficiency = (avg_instructions / ecore_total_energy) / 1e6 if ecore_total_energy > 0 else np.nan
        pcore_efficiency = (avg_instructions / pcore_total_energy) / 1e6 if pcore_total_energy > 0 else np.nan

        # Calculate percentage improvements
        pcore_faster_percentage = ((ecore_total_time - pcore_total_time) / ecore_total_time) * 100 if ecore_total_time > 0 else np.nan
        ecore_more_efficient_percentage = ((ecore_efficiency - pcore_efficiency) / pcore_efficiency) * 100 if pcore_efficiency > 0 else np.nan

        # Format energy in scientific notation
        ecore_total_energy_formatted = f"{ecore_total_energy:.2e}"
        pcore_total_energy_formatted = f"{pcore_total_energy:.2e}"

        # Add the row to the LaTeX table
        row = (
            f"{application_name} & {ecore_total_time:.2f} & {ecore_total_energy_formatted} & {ecore_efficiency:.2f} "
            f"& {pcore_total_time:.2f} & {pcore_total_energy_formatted} & {pcore_efficiency:.2f} "
            f"& {avg_millions_instr:.2f} & {pcore_faster_percentage:.2f} & {ecore_more_efficient_percentage:.2f} \\\\"
        )
        rows.append(row)

    rows.append(r"\hline")
    rows.append(r"\end{tabular}")
    rows.append(rf"\caption{{Performance and {energy_type.capitalize()} Energy Efficiency Comparison between E-cores and P-cores at {frequency}}}")
    rows.append(rf"\label{{tab:{energy_type}_{frequency}_comparison}}")
    rows.append(r"\end{table*}")

    # Output the LaTeX table
    latex_table = "\n".join(rows)
    print(latex_table)

# Main function to generate tables for all frequencies and energy types
def main():
    energy_types = ["pkg", "psys", "cores"]
    #frequencies = ["1500MHz", "2000MHz", "2500MHz", "3000MHz", "3500MHz"]
    frequencies = ["2500MHz", "3500MHz"]

    for energy_type in energy_types:
        for frequency in frequencies:
            print(f"\nGenerating table for {energy_type} at {frequency}...\n")
            generate_latex_table(energy_type, frequency)

if __name__ == "__main__":
    main()
