from typing import Any
from matplotlib.axes import Axes 
from matplotlib import pyplot as plt

from .result_clip import ResultClip, ExperimentResultWrapper, Figure, ResultClipUtils
from core.postprocessing.analysis.trace_provider import TraceProvider 

class AppExecutionClip(ResultClip):
    """
    This clip creates a horizontal bar plot showing the execution ranges of application instances.
    The granularity is at the instance level, meaning each bar represents the lifetime of an application instance.
    Works with all monitoring modes.

    Parameters
    ----------

    color_map: str | None
        The name of the matplotlib colormap to use for coloring different application instances.
        See https://matplotlib.org/stable/tutorials/colors/colormaps.html for available colormaps.
    """
    def __init__(self, color_map: str | None = "CMRmap") -> None:
        self._color_map = plt.get_cmap(color_map)

    @property
    def clip_filename(self) -> str:
        return "app_execution_plot"
    
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
        
        fig_width = 6
        fig_height = 1 + len(trace_provider.get_instance_ids()) * 0.5
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), layout='constrained')

        # Determine colors for each instance
        instance_ids = trace_provider.get_instance_ids()
        instance_to_color = {iid: self._color_map(i / len(instance_ids)) for i, iid in enumerate(instance_ids)}

        # Plot execution ranges
        bar_position = 0
        x_ticks: list[int] = []
        x_labels: list[str] = []
        
        for app_name, instance_ids in trace_provider.get_app_index().items():
            short_app_name = ResultClipUtils.strip_application_label(app_name)
            for iid in instance_ids:
                start, end = trace_provider.get_execution_range(instance_id=iid)
                if not start and not end:
                    continue

                start_time, end_time = start, end
                app_label = f"{short_app_name} ({iid})" if len(instance_ids) > 1 else short_app_name
                x_ticks.append(bar_position)
                x_labels.append(app_label)
                ax.barh(
                    y=bar_position,
                    width=end_time - start_time,
                    left=start_time,
                    color=instance_to_color[iid],
                    height=0.8,
                    label=f"Instance {iid}",
                )
                bar_position -= 1

        ax.set_xlabel("Time (s)")
        ax.set_title("Application Execution Ranges")
        ax.set_yticks(x_ticks)
        ax.set_yticklabels(x_labels)
        ax.set_axisbelow(True)
        ax.grid(True, which='both', axis='y', linestyle='--', linewidth=0.5)

        return fig
        