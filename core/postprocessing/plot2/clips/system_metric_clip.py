from typing import Any
from matplotlib import pyplot as plt
from matplotlib.axes import Axes

from core.postprocessing.plot2.clips.result_clip import ResultClip, ExperimentResultWrapper, Figure
from core.postprocessing.analysis2.trace_provider import TraceProvider

class SystemMetricClip(ResultClip):
    def __init__(self, system_metrics: set[str] | None = None) -> None:
        self._sys_metrics_to_plot = system_metrics

    @property
    def clip_filename(self) -> str:
        return "system_metric_plot"
    
    @property
    def style(self) -> dict[str, Any] | None:
        return {
            'text.usetex': True,
            'font.family': 'serif',
            'axes.labelsize': 14,
            'axes.titlesize': 14,
            'legend.fontsize': 16,
            'xtick.labelsize': 14,
            'ytick.labelsize': 14,
            'figure.titlesize': 16
        }
    
    def create_plot(self, result_wrapper: ExperimentResultWrapper) -> Figure:

        # Get trace provider
        trace_provider: TraceProvider = result_wrapper.get_trace_provider()
        available_metrics = trace_provider.available_sys_metrics
        metrics = self._sys_metrics_to_plot or available_metrics

        # Determine plot parameters
        column_count = min(4, len(available_metrics))
        row_count = (len(available_metrics) + column_count - 1) // column_count
        fig_size = (3 * column_count, 2.5 * row_count)

        fig, axes = plt.subplots(figsize=fig_size, ncols=column_count, nrows=row_count, constrained_layout=True)
        axs: list[Axes] = axes.flatten() if len(available_metrics) > 1 else [axes]

        # Warn about unavailable metrics
        unavailable_metrics = [m for m in metrics if m not in available_metrics]
        if unavailable_metrics:
            print(f"[SystemMetricClip] Warning: The following system metrics are not available: {', '.join(unavailable_metrics)}")
            print(f"[SystemMetricClip] Available system metrics: {', '.join(available_metrics)}")

        # Plot each metric
        for i, metric in enumerate(sorted(metrics)):
            ax = axs[i]
            
            # Add placeholder if metric not available
            if metric not in available_metrics:
                ax.text(
                    x=0.5, y=0.5, 
                    s=f"Metric '{metric}' not available.\n\nAvailable metrics:\n" + "\n".join(available_metrics),
                    ha='center', va='center', wrap=True
                )
                continue
            
            x, y = trace_provider.get_sys_metric_trace(metric)
            ax.plot(x, y, label=metric)
            ax.set_xlabel("Time (s)")
            ax.set_ylabel(metric.capitalize())
            ax.set_title(f"{metric.capitalize()}")
            ax.grid(True, axis='both', which='both', linestyle='-', linewidth=0.8, color='#000', alpha=0.2)

        return fig
