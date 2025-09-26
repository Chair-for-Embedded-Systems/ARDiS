from typing import Any
from matplotlib.axes import Axes 
from matplotlib import pyplot as plt

from .result_clip import ResultClip, ExperimentResultWrapper, Figure, ResultClipUtils
from core.postprocessing.analysis.trace_provider import TraceProvider 


class ThreadExecutionClip(ResultClip):

    """
    This clip visualizes the execution ranges of threads over time.
    Each horizontal bar represents the active execution period of a thread, with the main thread of each
    application instance highlighted distinctly.

    Parameters
    ----------
    iids: set[int] | None
        A set of instance IDs to include in the plot. If None, all instances are included.
    color_map: str
        The name of the matplotlib colormap to use for coloring different application instances.
        See https://matplotlib.org/stable/tutorials/colors/colormaps.html for available colormaps.
    """
    def __init__(self, iids: set[int] | None = None, color_map: str = "CMRmap") -> None:
        if iids is not None and len(iids) == 0:
            raise ValueError("If provided, the set of instance IDs must not be empty.")
        self._color_map = plt.get_cmap(color_map)
        self._selected_iids = iids

    @property
    def clip_filename(self) -> str:
        iid_part = "_iids_" + "_".join(map(str, sorted(self._selected_iids))) if self._selected_iids else ""
        return f"thread_execution_plot{iid_part}"
    
    @property
    def style(self) -> dict[str, Any] | None:
        return {
           'text.usetex': True,
            'font.family': 'serif',
            'axes.labelsize': 12,
            'axes.titlesize': 14,
            'legend.fontsize': 14,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10
        }

    def create_plot(self, result_wrapper: ExperimentResultWrapper) -> Figure:
        
        trace_provider = result_wrapper.get_trace_provider()
        
        # Check that there are threads in the dataset
        if self._selected_iids is not None:
            thread_count = sum(len(trace_provider.get_threads(iid)) for iid in self._selected_iids)
        else:
            thread_count = len(trace_provider.get_thread_ids())
        
        if thread_count == 0:
            raise ValueError("No threads found in the trace data. Ensure that the monitoring mode includes thread information.")

        # Determine figure dimensions based on thread count
        figure_width = 6
        figure_height = min(4, thread_count * 0.4)
        fig, ax = plt.subplots(figsize=(figure_width, figure_height))

        # Calulate colors for each application instance
        cmap = self._color_map
        instance_ids = trace_provider.get_instance_ids()
        instance_to_color = {iid: cmap(i / len(instance_ids)) for i, iid in enumerate(instance_ids)}

        bar_position = 0
        y_ticks: list[int] = []
        y_labels: list[str] = []

        for app_name, instance_ids in (trace_provider.get_app_index().items()):
            short_app_name = ResultClipUtils.strip_application_label(app_name)
            for iid in instance_ids:
                # Skip instance that are not selected
                if self._selected_iids is not None and iid not in self._selected_iids:
                    continue
                
                # Determine colors for main and working threads
                saturation = 0.6
                color_main_thread = instance_to_color[iid]
                color_working_thread = tuple(saturation * c + (1 - saturation) * 1.0 for c in color_main_thread[:3])

                # Plot each thread of this instance
                # Since tids/pids are consecutively assigned in linux, we can assume that the lowest is the main thread
                for thread_index, tid in enumerate(sorted(trace_provider.get_threads(iid))):
                    start_time, end_time = trace_provider.get_execution_range(instance_id=iid, thread_id=tid)
                    duration = end_time - start_time
                    
                    # Style main thread differently
                    if thread_index == 0:
                        app_label = f"{short_app_name}"  
                        color = color_main_thread
                        bar_height = 0.9
                    else:
                        app_label = f"t-{thread_index}"
                        color = color_working_thread
                        bar_height = 0.7

                    # Save y-tick and label for this bar for later
                    y_ticks.append(bar_position)
                    y_labels.append(app_label)

                    ax.barh(y = bar_position, width = duration, left = start_time,
                            height = bar_height, tick_label = app_label, color = color)
                    
                    # Proceed to next bar position
                    bar_position -= 1

                # Add extra space after each instance
                bar_position -= 1    

        # Decorate plot
        ax.set_xlabel("Time (s)")
        ax.set_title("Thread Execution Ranges")
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_labels)
        ax.set_axisbelow(True)
        ax.grid(which='both', axis='y', linestyle='--', linewidth=0.5)

        return fig        