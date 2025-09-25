from typing import Any
from matplotlib import pyplot as plt
from matplotlib.axes import Axes

from core.postprocessing.plot2.clips.result_clip import ResultClip, ExperimentResultWrapper, Figure
from core.postprocessing.analysis2.trace_provider import TraceProvider

class SystemMetricClip(ResultClip):
    """
    This clip creates a grid of line plots for multiple system-level metrics.
    Each subplot corresponds to one metric, showing its evolution over time.
    
    Parameters
    ----------
    system_metrics: set[str] | None
        A set of system metric names to plot. If None, all available system metrics will be plotted.
    """
    def __init__(self, system_metrics: set[str] | None = None) -> None:
        if system_metrics is not None and len(system_metrics) == 0:
            raise ValueError("System metrics set must not be empty if provided.")
        self._sys_metrics_to_plot = system_metrics

    @property
    def clip_filename(self) -> str:
        metric_part = f"_{'_'.join(sorted(self._sys_metrics_to_plot))}" if self._sys_metrics_to_plot else ""
        return f"system_metric_plot{metric_part}"

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

        # Check for unavailable metrics
        unavailable_metrics = [m for m in metrics if m not in available_metrics]
        if unavailable_metrics:
            raise ValueError(f"Some specified system metrics are not available: {unavailable_metrics}. Available metrics: {available_metrics}")

        # Determine plot parameters
        column_count = min(4, len(available_metrics))
        row_count = (len(available_metrics) + column_count - 1) // column_count
        fig_size = (3 * column_count, 2.5 * row_count)

        fig, axes = plt.subplots(figsize=fig_size, ncols=column_count, nrows=row_count, constrained_layout=True)
        axs: list[Axes] = axes.flatten() if len(available_metrics) > 1 else [axes]

        # Plot each metric
        for i, metric in enumerate(sorted(metrics)):
            ax = axs[i]
            x, y = trace_provider.get_sys_metric_trace(metric)
            ax.plot(x, y, label=metric)
            ax.set_xlabel("Time (s)")
            ax.set_ylabel(metric.capitalize())
            ax.set_title(f"{metric.capitalize()}")
            ax.grid(True, axis='both', which='both', linestyle='-', linewidth=0.8, color='#000', alpha=0.2)

        return fig
