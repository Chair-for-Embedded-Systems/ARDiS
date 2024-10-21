import os
import re
import numpy as np
import glob
import sys
import matplotlib.pyplot as plt

# Import the configuration
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
import config

# Enable LaTeX rendering in Matplotlib (if needed)
plt.rcParams.update({
    "text.usetex": True,  # Use LaTeX to render text
    "font.family": "serif",  # Use serif fonts
    "font.serif": ["Times"],  # Use Times font for the plot
    "axes.labelsize": 14,  # Font size for axis labels
    "xtick.labelsize": 10,  # Font size for x-axis tick labels
    "ytick.labelsize": 10,  # Font size for y-axis tick labels
    "legend.fontsize": 14,  # Font size for the legend
    "axes.titlesize": 14  # Font size for the title
})

frequencies = [1800, 2500, 3400]

per_freq_line_colors = {
    freq: color for freq, color in zip(frequencies, ['#f7dc8e', '#5497f7', '#b88acf'])
}
per_freq_highlight_colors = {
    freq: color for freq, color in zip(frequencies, ['#fff2cc', '#dae8fc', '#e1d5e7'])
}
per_freq_labels = {
    freq: label for freq, label in zip(frequencies, ['Config 1', 'Config 2', 'Config C'])
}
# Function to parse log file and extract instructions
def parse_log_file(log_file):
    exec_time_points = []
    instantaneous_instructions = []

    with open(log_file, 'r') as file:
        for line in file:
            if "] PID" in line:
                match = re.search(r'\[(\d+\.\d+)s\].*instructions = (\d+)', line)
                if match:
                    time = float(match.group(1))
                    instructions = int(match.group(2))  # Instantaneous instructions from the log
                    exec_time_points.append(time)
                    instantaneous_instructions.append(instructions)

    return exec_time_points, instantaneous_instructions

# Function to highlight a randomly selected slice
def highlight_instruction_slice(start_instr, end_instr, cumulative_instructions, time_points, duration, frequency):
    start_time = np.interp(start_instr, cumulative_instructions, time_points)
    end_time = np.interp(end_instr, cumulative_instructions, time_points)
    plt.axvspan(start_time, end_time, color=per_freq_highlight_colors[frequency], label=f"{per_freq_labels[frequency]}")

# Function to generate slices and highlight a selected slice
def generate_slices_instructions(application_name, core_type, log_files, frequencies, instruction_slice, highlight_start, highlight_end):
    for freq, log_file in zip(frequencies, log_files):
        if not os.path.exists(log_file):
            print(f"Log file not found for {core_type} at {freq} MHz: {log_file}")
            continue

        time_points, instantaneous_instructions = parse_log_file(log_file)
        cumulative_instructions = np.cumsum(instantaneous_instructions)

        # Plot cumulative instructions
        plt.plot(time_points, cumulative_instructions, color=per_freq_line_colors[freq], linewidth=1.5)

        # Highlight a slice
        highlight_instruction_slice(highlight_start, highlight_end, cumulative_instructions, time_points, highlight_end - highlight_start, freq)

    # Plot horizontal lines at highlight_start and highlight_end
    plt.axhline(y=highlight_start, color='#009688', linestyle='--', label='Slice Delimiters', alpha=0.5)
    plt.axhline(y=highlight_end, color='#009688', linestyle='--', alpha=0.5)
    plt.ylim(ymax=7.2e10)
    plt.xlabel("Time (s)")
    plt.ylabel("Cumulative Instructions")
    plt.title(f"Cumulative Instructions over Time for Application A")
    plt.legend(loc='upper left')

def main():
    log_directory = config.PARSEC_FIXED_FREQ_FOLDER
    application_name = "parsec-blackscholes"
    print(f"\nProcessing {application_name}...")

    pcore_files = [glob.glob(os.path.join(log_directory, f"*_{application_name}_{freq}MHz_Pcore/periodic_counters.log")) for freq in frequencies]
    pcore_files = [item for sublist in pcore_files for item in sublist]

    if not pcore_files:
        print(f"Skipping {application_name}: Missing log files.")
        return

    instruction_slice = 1e9
    random_start_instruction = 2e10
    random_end_instruction = 3e10

    plt.figure(figsize=(7, 3.4))

    generate_slices_instructions(application_name, "P-core", pcore_files, frequencies, instruction_slice, random_start_instruction, random_end_instruction)

    plt.tight_layout(pad=1.0)
    output_image_file = f"{application_name}_highlighted_energy_slicing_plot.png"
    plt.savefig(output_image_file, dpi=300, format='png')
    print(f"Figure saved as {output_image_file}")

if __name__ == "__main__":
    main()