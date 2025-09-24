from typing import Any
from core.postprocessing.plot2.result_plotter import ResultPlotter
from core.postprocessing.analysis2.trace_provider import TraceProvider
import os

import matplotlib.pyplot as plt
from matplotlib.axes import Axes

class BasicPlotter(ResultPlotter):
    
    style: dict[str, Any] = {
        'text.usetex': True,
        'font.family': 'serif',
        'axes.labelsize': 12,
        'axes.titlesize': 14,
        'legend.fontsize': 14,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10
    }

    def __init__(self) -> None:
        super().__init__()

    def plot_results(self, expertiment_folder: str, output_folder: str | None = None):
        print(f"Plotting results from: {expertiment_folder}")
        
        if output_folder is None:
            output_folder = os.path.join(expertiment_folder, "plots")
        os.makedirs(output_folder, exist_ok=True)

        # Load data
        results = self._load_results(expertiment_folder)
        trace_provider = TraceProvider(results)
        
        with plt.style.context(self.style):            
            self._plot_combined_metric(
                trace_provider=trace_provider,
                metrics=sorted(trace_provider.available_app_metrics, key=lambda s: s.lower()),
                output_folder=output_folder
            )

    
    def _plot_combined_metric(self, trace_provider: TraceProvider, metrics: list[str], output_folder: str) -> None:
        
        # Amount of instances to plot
        cmap = plt.get_cmap("CMRmap")
        instance_ids = [iid for iids in trace_provider.get_app_index().values() for iid in iids]
        instance_to_color = {iid: cmap(i / len(instance_ids)) for i, iid in enumerate(instance_ids)}

        # Check if all metrics are available
        for metric in metrics:
            if metric not in trace_provider.available_app_metrics:
                raise ValueError(f"Metric '{metric}' is not available in the trace provider.")
            
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
        fig.legend(handles, labels, loc='upper center', bbox_to_anchor=(0.5, 1.1), ncol=int(len(labels)))
        output_file = os.path.join(output_folder, "combined.png")
        print(f"Saving combined plot to: {output_file}")
        fig.savefig(output_file, dpi=300, bbox_inches='tight')

    def _plot_metric(self, trace_provider: TraceProvider, metric: str, ax: Axes, x_label: str | None = None, y_label: str | None = None) -> None:

        app_index = trace_provider.get_app_index()

        
        instance_ids = [iid for iids in app_index.values() for iid in iids]
        cmap = plt.get_cmap("CMRmap")
        instance_to_color = {iid: cmap(i / len(instance_ids)) for i, iid in enumerate(instance_ids)}

        for app_name, instance_ids in app_index.items():
            for iid in instance_ids:
                app_label = f"{app_name} <{iid}>"
                (x, y) = trace_provider.get_app_metric_trace(metric=metric, instance_id=iid)
                ax.plot(x, y, label=app_label, color=instance_to_color[iid])
                if x_label is not None:
                    ax.set_xlabel(x_label)
                if y_label is not None:
                    ax.set_ylabel(y_label)
                ax.grid(True, axis='both', which='both', linestyle='-', linewidth=0.8, color='#000', alpha=0.2)

if __name__ == "__main__":
    
    core_experiment = "/home/uhqql/ARDIS/results/2025-09-23_17-54-09_Simple_Experiment_with_Specific_Applications"
    pid_experiment = "/home/uhqql/ARDIS/results/2025-09-23_17-55-37_Simple_Experiment_with_Specific_Applications"
    tid_experiment = "/home/uhqql/ARDIS/results/2025-09-23_17-56-51_Experiment_with_tid_monitoring"

    multiple_instance_experiment = "/home/uhqql/ARDIS/results/2025-09-24_15-16-33_Experiment_with_multiple_instances"

    plotter = BasicPlotter()
    plotter.plot_results(multiple_instance_experiment)
