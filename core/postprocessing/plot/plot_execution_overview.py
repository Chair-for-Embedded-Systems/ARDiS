import os
import numpy as np
from matplotlib import pyplot as plt


def plot_execution_overview(
    output_file: str | None,
    data: list[tuple[str, float, float]],
    verbose: bool = False,
    show: bool = False,
) -> None:
    """
    Creates a plot that visualizes the execution range for each application as horizontal bar chart.

    Parameters
    ----------
    data: list[tuple[str, float, float]]
        The data that is used for the plot i.e. `list(app_name, start_time_sec, end_time_sec)`
    verbose: bool
        Specifies if the plot generation should be verbose (print output_file to console). Defaults to False
    show: bool
        Flag to enable `plt.show()` (requires gui backend)
    """
    y = np.arange(len(data))
    sorted_data = data.copy()
    sorted_data.sort(key=lambda x: x[0], reverse=True)
    
    _, axis = plt.subplots(figsize=(8, len(y) * 0.2 + 1))
    
    for i, (app, start, end) in enumerate(sorted_data):
        axis.barh(y=i, width=end-start, left=start, label=app)
    
    axis.set_title("Overview Execution")
    axis.set_xlabel("Time (s)")
    axis.set_yticks(ticks=y, labels=[app for (app, _, _) in sorted_data])
    axis.set_axisbelow(True)
    axis.grid(visible=True, axis="both")
    
    if output_file:
        os.makedirs(os.path.dirname(output_file), exist_ok=True)
        plt.savefig(output_file, dpi=200, format='png', bbox_inches='tight')
        if verbose:
            print("Plotting", output_file)
    
    if show:
        plt.show()

    plt.close() 


def __mock_plot():
    plot_execution_overview(
        output_file=None,
        data=[
            ("blackscholes", 5.0, 30.0),
            ("bodytrack", 10.0, 40.0),
            ("bodytrack", 15.0, 45.0),
            ("bodytrack", 20.0, 50.0),
        ],
        show=True
    )

if __name__ == "__main__":
    __mock_plot()