from typing import Any
from matplotlib.axes import Axes 
from matplotlib import pyplot as plt

from .result_clip import ResultClip, ExperimentResultWrapper, Figure
from core.postprocessing.analysis2.trace_provider import TraceProvider 

class AppLifeTimeClip(ResultClip):
    """
    Figure clip that creates a plot showing the lifetime of applications.
    """
    def __init__(self, color_map: str | None = "CMRmap") -> None:
        self._color_map = plt.get_cmap(color_map)

    @property
    def clip_filename(self) -> str:
        return "app_lifetime_plot"
    
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
        # Implementation for creating a plot showing application lifetimes
        
        # Load data
        trace_provider = result_wrapper.get_trace_provider()
        
        fig, ax = plt.subplots(figsize=(6, 4))
        self._plot_app_lifetimes(trace_provider, ax)

        return fig
        

    def _plot_app_lifetimes(self, trace_provider: TraceProvider, ax: Axes) -> None:
        
        # Amount of instances to plot
        cmap = self._color_map
        instance_ids = [iid for iids in trace_provider.get_app_index().values() for iid in iids]
        instance_to_color = {iid: cmap(i / len(instance_ids)) for i, iid in enumerate(instance_ids)}

        # Plot lifetimes
        for app_id, instance_ids in trace_provider.get_app_index().items():
            for iid in instance_ids:
                start, end = trace_provider.get_execution_range(instance_id=iid)
                if not start and not end:
                    continue

                start_time, end_time = start, end
                app_label = f"{app_id} ({iid})" if len(instance_ids) > 1 else app_id
                ax.barh(
                    y=app_label,
                    width=end_time - start_time,
                    left=start_time,
                    color=instance_to_color[iid],
                    height=0.3,
                    label=f"Instance {iid}",
                )

        ax.set_xlabel("Time (s)")
        ax.set_title("Application Lifetimes")
        ax.set_axisbelow(True)
        ax.grid(True, which='both', axis='y', linestyle='--', linewidth=0.5)

class ThreadExecutionClip(ResultClip):

    """
    Figure clip that creates a plot showing the lifetime of application threads.
    """
    def __init__(self, color_map: str | None = "CMRmap") -> None:
        self._color_map = plt.get_cmap(color_map)

    @property
    def clip_filename(self) -> str:
        return "thread_execution_plot"
    
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
        # Implementation for creating a plot showing application lifetimes
        
        # Load data
        trace_provider = result_wrapper.get_trace_provider()
        
        fig, ax = plt.subplots(figsize=(6, 4))
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

        for app_id, instance_ids in (trace_provider.get_app_index().items()):
            for iid in instance_ids:
                threads = trace_provider.get_threads(iid)

                color_main_thread = instance_to_color[iid]
                # Lighten the color for non-main threads
                saturation = 0.6
                color_working_thread = tuple(saturation * c + (1 - saturation) * 1.0 for c in color_main_thread[:3])

                # Plot each thread
                for thread_index, tid in enumerate(sorted(threads)):
                    start_time, end_time = trace_provider.get_execution_range(instance_id=iid, thread_id=tid)
                    
                    is_main_thread = (thread_index == 0)
                    app_label = f"{app_id}" if is_main_thread else f"t-{thread_index}"

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
                    app_label = f"{app_id} ({iid})" if len(instance_ids) > 1 else app_id
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

        