from collections import defaultdict
from typing import Any

from matplotlib import pyplot as plt
from matplotlib.axes import Axes
from matplotlib.colors import Colormap

from core.postprocessing.clips.result_clip import ResultClip, ExperimentResultWrapper, Figure, ResultClipUtils
from core.postprocessing.analysis.trace_provider import TraceProvider
from core.postprocessing.clips.app_mapping_clip import AppMappingClip

class ThreadMappingClip(ResultClip):
    """
    This clip visualizes the mapping of threads to CPU cores for an instance over time.
    Every horizontal bar represents the mapping of a thread to a CPU core.
    Each individual subplot represents one application instance.

    Parameters
    ----------
    iids: set[int] | None
        A set of instance IDs to include in the plot. If None, all instances are included
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
        return f"thread_mapping_plot{iid_part}"
    
    @property
    def style (self) -> dict[str, Any] | None:
        return {
            'text.usetex': True,
            'font.family': 'serif',
            'axes.labelsize': 14,
            'axes.titlesize': 14,
            'legend.fontsize': 12,
            'xtick.labelsize': 14,
            'ytick.labelsize': 14,
            'figure.titlesize': 16
        }

    def create_plot(self, result_wrapper: ExperimentResultWrapper) -> Figure:
        trace_provider = result_wrapper.get_trace_provider()
        
        # Check if experiment contains valid data
        if len(trace_provider.get_thread_ids()) == 0:
            raise ValueError(
                "No threads found in the trace data. "
                "Ensure that the monitoring mode includes thread information."
            )

        # Determine which instances should be plotted
        available_iids = trace_provider.get_instance_ids()
        if self._selected_iids is not None:
            instance_to_plot = available_iids.intersection(self._selected_iids)
            if instance_to_plot != self._selected_iids:
                raise ValueError(
                    f"Some specified instance IDs are not available: "
                    f"{self._selected_iids - available_iids}. "
                    f"Available instances: {available_iids}"
                )
        else:
            instance_to_plot = available_iids

        thread_to_affinity_ranges = self._get_thread_affinity_ranges(trace_provider)
        
        # Determine amount of columns and rows for the subplot grid
        instance_count = len(instance_to_plot)
        subplot_columns = min(3, instance_count)
        subplot_rows = (instance_count + subplot_columns - 1) // subplot_columns

        # Create figure
        fig, axs = plt.subplots(  # type: ignore
            figsize=(8 * subplot_columns, max(5, subplot_rows * 3)), 
            nrows=subplot_rows, ncols=subplot_columns, layout='constrained'
        )
        axs: list[Axes] = axs.flatten() if instance_count > 1 else [axs]  # type: ignore

        axis_iter = iter(axs)
        for app_name, instance_ids in trace_provider.get_app_index().items():
            short_app_name = ResultClipUtils.strip_application_label(app_name)
            for iid in instance_ids:
                # Skip instance that are not selected
                if iid not in instance_to_plot:
                    continue
                
                # Select threads that belong to this instance
                relevant_threads = {
                    tid: ranges for tid, ranges in thread_to_affinity_ranges.items() 
                    if tid in trace_provider.get_threads(iid)
                }
                # Plot thread mapping for this instance
                ax: Axes = next(axis_iter)
                self._plot_thread_mapping(
                    ax=ax,
                    thread_to_affinity_ranges=relevant_threads
                    ,cmap=self._color_map)
                ax.set_title(f"{short_app_name} ({iid})" if len(instance_ids) > 1 else f"{short_app_name}")
            
        return fig
    
    @staticmethod
    def _plot_thread_mapping(
        ax: Axes,
        thread_to_affinity_ranges: dict[int, dict[int, list[tuple[float, float]]]],
        cmap: Colormap
    ) -> None:
        
        # Calculate colors and positions
        thread_ids = sorted(thread_to_affinity_ranges.keys())
        thread_to_color = {tid: cmap(i / len(thread_ids)) for i, tid in enumerate(thread_ids)}
        utilized_cores = sorted({core for ranges in thread_to_affinity_ranges.values() for core in ranges.keys()})
        
        # Simulate placement of bars to determine max threads per core
        # Iterate from oldest to newest thread and greedy place in the first available slot.
        # A slot is available if the start time of the new bar is after the end time of the last bar in that slot.
        # If no slot is available, create a new one
        core_to_slot_occupation: dict[int, list[float]] = {core: [0.0] for core in utilized_cores}
        for thread_index, tid in enumerate(sorted(thread_to_affinity_ranges.keys())):
            for core in thread_to_affinity_ranges[tid].keys():
                affinity_ranges = thread_to_affinity_ranges[tid]
                for start, end in affinity_ranges[core]:
                    for slot_index in range(len(core_to_slot_occupation[core])):
                        if start >= core_to_slot_occupation[core][slot_index]:
                            core_to_slot_occupation[core][slot_index] = end
                            break
                    else:
                        core_to_slot_occupation[core].append(end)
        
        # Detemine the upper bound of threads per core
        max_threads_per_core = {core: len(core_to_slot_occupation[core]) for core in utilized_cores}
        max_threads = max(max_threads_per_core.values())

        bar_height = 1 / max_threads
        core_to_y = {core: -i * 2  for i, core in enumerate(utilized_cores)}

        core_to_slot_occupation = {core: [0] for core in utilized_cores}
        # Plot bars for each thread's affinity ranges
        for thread_index, tid in enumerate(sorted(thread_to_affinity_ranges.keys())):
            bar_color = thread_to_color[tid]
            affinity_ranges = thread_to_affinity_ranges[tid]
            label = f"T-{thread_index}"
            label_once = label  # To only label the first bar for the legend
            
            for core, time_ranges in affinity_ranges.items():
                for start, end in time_ranges:
                    
                    # Here we are doing the same greedy placement as above to determine the offset.
                    # However, now we actually plot the bars. This double computation is a bit redundant,
                    # but it keeps the code simpler.
                    slots = core_to_slot_occupation[core]
                    for slot_index in range(len(slots)):
                        if start >= slots[slot_index]:
                            core_to_slot_occupation[core][slot_index] = end
                            break
                    else:
                        slot_index = len(slots)
                        core_to_slot_occupation[core].append(end)
                        
                    offset = slot_index * bar_height
                    ax.barh(
                        y=core_to_y[core] - offset,
                        width=end - start, left=start,
                        color=bar_color, height=bar_height,
                        label=label_once,
                        align='edge'
                    )
                    label_once = None
        
        # Add dashed lines to separate cores visually
        for y_pos in core_to_y.values():
            padding = bar_height * 0.5
            upper_line = y_pos + bar_height + padding
            lower_line = y_pos + bar_height - 1 - padding
            ax.axhline(y=upper_line, color='black', linestyle='--', linewidth=.75, alpha=0.2)
            ax.axhline(y=lower_line, color='black', linestyle='--', linewidth=.75, alpha=0.2)

        # Axis decorations
        ax.set_yticks([core_to_y[core] + bar_height - 0.5 for core in utilized_cores])
        ax.set_yticklabels([f"Core {core}" for core in utilized_cores])
        ax.set_xlabel("Time (s)")
        ax.set_axisbelow(True)

        # Adjust legend based on number of threads
        legend_columns = min(6, len(thread_ids))
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, -0.2), ncol=legend_columns)

    @staticmethod
    def _get_thread_affinity_ranges(trace_provider: TraceProvider) -> dict[int, dict[int, list[tuple[float, float]]]]:
        
        instance_to_affinity_ranges: dict[int, dict[int, list[tuple[float, float]]]] = defaultdict(dict)
        
        for _, instance_ids in trace_provider.get_app_index().items():
            for iid in instance_ids:
                for thread_id in trace_provider.get_threads(iid):
                    timestamps, affinity = trace_provider.get_affinity_trace(iid, thread_id)
                    affinity_index_ranges = AppMappingClip.find_contiguous_ranges(affinity) # type: ignore
                    # Map indexed affinity ranges to timestamp ranges
                    affinity_timestamp_ranges = {
                        core: [(timestamps[start], timestamps[min(end + 1, len(timestamps) - 1)]) 
                               for start, end in ranges] 
                               for core, ranges in affinity_index_ranges.items()
                    }
                    instance_to_affinity_ranges[thread_id] = affinity_timestamp_ranges
        
        return instance_to_affinity_ranges
