from typing import Any
from matplotlib.axes import Axes 
from matplotlib import pyplot as plt

from .result_clip import ResultClip, ExperimentResultWrapper, Figure
from core.postprocessing.analysis2.trace_provider import TraceProvider 


class AppMultiMetricClip(ResultClip):
    """
    This clip creates a grid of line plots for multiple application-level metrics.
    Each subplot corresponds to one metric, showing its evolution over time for each application instance.
    Works with all monitoring modes.
    
    Parameters
    ----------
    application_events: list[str] | None
        A list of application event names to plot. If None, all available application events will be plotted.
    iids: set[int] | None
        A set of instance IDs to include in the plot. If None, all instances are included.
    color_map: str
        The name of the matplotlib colormap to use for coloring different application instances.
        See https://matplotlib.org/stable/tutorials/colors/colormaps.html for available colormaps.
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

    def __init__(self, application_events: list[str] | None = None, iids: set[int] | None = None, color_map: str = "CMRmap") -> None:
        
        if application_events is not None and len(application_events) == 0:
            raise ValueError("Application events list must not be empty if provided.")
        
        if iids is not None and len(iids) == 0:
            raise ValueError("Instance IDs set must not be empty if provided.")
        
        self._metrics = application_events
        self._color_map = plt.get_cmap(color_map)
        self._iids = iids

    @property
    def clip_filename(self) -> str:
        # Generate a filename based on the selected metrics and instance IDs
        iid_part = "_iids_" + "_".join(map(str, sorted(self._iids))) if self._iids else ""
        metric_part = f"_{'_'.join(self._metrics)}" if self._metrics else ""
        return f"app_multi_metric_plot{iid_part}{metric_part}"
        
    @property
    def style(self) -> dict[str, Any] | None:
        return self._style

    def create_plot(self, result_wrapper: ExperimentResultWrapper) -> Figure:
        
        trace_provider = result_wrapper.get_trace_provider()

        if self._metrics:
            # Keep order metrics as specified by the user
            metrics = self._metrics
        else:
            # Sort metrics alphabetically for better readability
            metrics = sorted(trace_provider.available_app_metrics, key=lambda s: s.lower())
        
        fig = self._plot_combined_metric(trace_provider, metrics)

        return fig
        

    def _plot_combined_metric(self, trace_provider: TraceProvider, metrics: list[str]) -> Figure:
        
        # Cretate colormap for instances
        cmap = self._color_map
        instance_ids = [iid for iids in trace_provider.get_app_index().values() for iid in iids]
        instance_to_color = {iid: cmap(i / len(instance_ids)) for i, iid in enumerate(instance_ids)}

        # Check if all metrics are available
        for metric in metrics:
            if metric not in trace_provider.available_app_metrics:
                raise ValueError(f"Metric '{metric}' is not available in the trace provider. Available metrics: {trace_provider.available_app_metrics}")
            
        # Calculate grid for all subplots (max 4 columns)
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

        # Calculate legend layout (max 4 columns)
        legend_columns = min(4, len(labels))
        fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, 1), ncol=legend_columns)
        
        return fig