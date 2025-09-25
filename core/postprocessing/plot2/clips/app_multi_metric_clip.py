from typing import Any
from matplotlib.axes import Axes 
from matplotlib import pyplot as plt

from .result_clip import ResultClip, ExperimentResultWrapper, Figure
from core.postprocessing.analysis2.trace_provider import TraceProvider 


class AppMultiMetricClip(ResultClip):
    """
    Figure clip that creates a plot with multiple metrics.
    """

    _style: dict[str, str|int|bool] = {
        'text.usetex': True,
        'font.family': 'serif',
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'legend.fontsize': 14,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10
    }

    def __init__(self, metrics: list[str] | None = None, color_map: str | None = "CMRmap") -> None:
        self._metrics = metrics
        self._color_map = plt.get_cmap(color_map)

    @property
    def clip_filename(self) -> str:
        # Generate a filename based on the selected metrics
        if self._metrics:
            metric_part = "_".join(self._metrics)
            return f"multi_metric_plot_{metric_part}"
        else:
            return "multi_metric_plot"
    
    @property
    def style(self) -> dict[str, Any] | None:
        return self._style

    def create_plot(self, result_wrapper: ExperimentResultWrapper) -> Figure:
        # Implementation for creating a plot with multiple metrics
        
        # Load data
        trace_provider = result_wrapper.get_trace_provider()

        if self._metrics:
            metrics = self._metrics
        else:
            metrics = sorted(trace_provider.available_app_metrics, key=lambda s: s.lower())
        
        fig = self._plot_combined_metric(trace_provider, metrics)

        return fig
        

    def _plot_combined_metric(self, trace_provider: TraceProvider, metrics: list[str]) -> Figure:
        
        # Amount of instances to plot
        cmap = self._color_map
        instance_ids = [iid for iids in trace_provider.get_app_index().values() for iid in iids]
        instance_to_color = {iid: cmap(i / len(instance_ids)) for i, iid in enumerate(instance_ids)}

        # Check if all metrics are available
        for metric in metrics:
            if metric not in trace_provider.available_app_metrics:
                raise ValueError(f"Metric '{metric}' is not available in the trace provider. Available metrics: {trace_provider.available_app_metrics}")
            
        # Calculate grid dimensions to plot all metrics
        num_metrics = len(metrics)
        num_cols = 4
        if num_metrics <= num_cols:
            num_cols = num_metrics
            num_rows = 1
        else:
            num_rows = (num_metrics + 1) // num_cols

        # Create subplots
        fig, axes = plt.subplots(figsize=(num_cols * 3, num_rows * 2.5), ncols=num_cols, nrows=num_rows, constrained_layout=True)  # type: ignore
        
        # Flatten axes array if necessary
        axes : list[Axes] = [axes] if num_metrics == 1 else axes.flatten() # type: ignore
            
        for i, metric in enumerate(metrics):
            ax : Axes = axes[i] 

            # Capitalize first letter and keep the rest as is
            fancy_metric = metric[0].upper() + metric[1:]
            for app_name, instance_ids in trace_provider.get_app_index().items():
                for iid in instance_ids:
                    app_label = f"{app_name} ({iid})" if len(instance_ids) > 1 else app_name
                    (x, y) = trace_provider.get_app_metric_trace(metric=metric, instance_id=iid)
                    ax.plot(x, y, label=app_label, color=instance_to_color[iid])
                    ax.set_xlabel(xlabel="Time (s)")
                    ax.set_ylabel(ylabel=fancy_metric)
                    ax.set_title(label=fancy_metric)
                    ax.grid(True, axis='both', which='both', linestyle='-', linewidth=0.8, color='#000', alpha=0.2)

        handles, labels = axes[0].get_legend_handles_labels()

        # Conditional placement of the legend
        if num_rows == 1:
            fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 1.2), ncol=int(len(labels)))
        else:
            fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 1.1), ncol=int(len(labels)))

        return fig