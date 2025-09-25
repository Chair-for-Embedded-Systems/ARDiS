from typing import Any
from matplotlib.axes import Axes 
from matplotlib import pyplot as plt

from .result_clip import ResultClip, ExperimentResultWrapper, Figure
from core.postprocessing.analysis2.trace_provider import TraceProvider 

class AppExecutionClip(ResultClip):
    """
    Figure clip that creates a plot showing the lifetime of applications.
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
        
        instance_count = len([iid for iids in trace_provider.get_app_index().values() for iid in iids])
        
        fig_height = min(4, instance_count * 0.4)
        fig, ax = plt.subplots(figsize=(6, fig_height))

        self._plot_app_lifetimes(trace_provider, ax)

        return fig
        
    def _plot_app_lifetimes(self, trace_provider: TraceProvider, ax: Axes) -> None:
        
        # Amount of instances to plot
        cmap = self._color_map
        instance_ids = [iid for iids in trace_provider.get_app_index().values() for iid in iids]
        instance_to_color = {iid: cmap(i / len(instance_ids)) for i, iid in enumerate(instance_ids)}

        # Plot lifetimes
        bar_position = 0
        x_ticks: list[int] = []
        x_labels: list[str] = []
        for app_id, instance_ids in trace_provider.get_app_index().items():
            for iid in instance_ids:
                start, end = trace_provider.get_execution_range(instance_id=iid)
                if not start and not end:
                    continue

                start_time, end_time = start, end
                app_label = f"{app_id} ({iid})" if len(instance_ids) > 1 else app_id
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
