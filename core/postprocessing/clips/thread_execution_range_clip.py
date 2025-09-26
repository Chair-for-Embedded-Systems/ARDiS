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
        self._iids = iids

    @property
    def clip_filename(self) -> str:
        iid_part = "_iids_" + "_".join(map(str, sorted(self._iids))) if self._iids else ""
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
        
        # Load data
        trace_provider = result_wrapper.get_trace_provider()
        
        expected_bar_count = len(trace_provider.get_thread_ids())
        if expected_bar_count == 0:
            expected_bar_count = len(trace_provider.get_instance_ids())
            
        fig_height = min(4, expected_bar_count * 0.4)

        fig, ax = plt.subplots(figsize=(6, fig_height))
        self._plot_thread_lifetimes(trace_provider, ax)

        return fig

    def _plot_thread_lifetimes(self, trace_provider: TraceProvider, ax: Axes) -> None:

        # Calulate colors for each application instance
        cmap = self._color_map
        instance_ids = [iid for iids in trace_provider.get_app_index().values() for iid in iids]
        instance_to_color = {iid: cmap(i / len(instance_ids)) for i, iid in enumerate(instance_ids)}

        bar_position = 0
        y_ticks: list[int] = []
        y_labels: list[str] = []

        for app_name, instance_ids in (trace_provider.get_app_index().items()):
            short_app_name = ResultClipUtils.strip_application_label(app_name)
            for iid in instance_ids:
                # Skip instance if not in the selected set
                if self._iids is not None and iid not in self._iids:
                    continue

                threads = trace_provider.get_threads(iid)

                color_main_thread = instance_to_color[iid]
                # Lighten the color for non-main threads
                saturation = 0.6
                color_working_thread = tuple(saturation * c + (1 - saturation) * 1.0 for c in color_main_thread[:3])

                # Plot each thread
                for thread_index, tid in enumerate(sorted(threads)):
                    start_time, end_time = trace_provider.get_execution_range(instance_id=iid, thread_id=tid)
                    
                    is_main_thread = (thread_index == 0)
                    app_label = f"{short_app_name}" if is_main_thread else f"t-{thread_index}"

                    y_ticks.append(bar_position)
                    y_labels.append(app_label)
        
                    ax.barh(
                        y=bar_position,
                        width=end_time - start_time,
                        tick_label=app_label,
                        left=start_time,
                        color=color_main_thread if is_main_thread else color_working_thread,
                        height=0.9 if is_main_thread else 0.7,
                    )
                    bar_position -= 1
                
                # Fallback in case no threads are found (wrong monitoring mode was used)
                if len(threads) == 0:
                    # No threads found, just plot the instance
                    start_time, end_time = trace_provider.get_execution_range(instance_id=iid)
                    app_label = f"{app_name} ({iid})" if len(instance_ids) > 1 else app_name
                    y_ticks.append(bar_position)
                    y_labels.append(app_label)
                    ax.barh(
                        y=bar_position,
                        width=end_time - start_time,
                        tick_label=app_label,
                        left=start_time,
                        color=color_main_thread,
                        height=0.9,
                    )
                    bar_position -= 1

                bar_position -= 1    

        ax.set_xlabel("Time (s)")
        ax.set_title("Thread Execution Ranges")
        ax.set_yticks(y_ticks)
        ax.set_yticklabels(y_labels)
        ax.set_axisbelow(True)
        ax.grid(True, which='both', axis='y', linestyle='--', linewidth=0.5)

        