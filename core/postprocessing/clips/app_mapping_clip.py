from collections import defaultdict
from typing import Any
from matplotlib import pyplot as plt

from core.postprocessing.clips.result_clip import ResultClip, ExperimentResultWrapper, Figure
from core.postprocessing.analysis.trace_provider import TraceProvider

class AppMappingClip(ResultClip):
    """
    This clip visualizes the mapping of application instances to CPU cores over time.
    The granularity is at the instance level, meaning each bar represents the mapping of an application instance to a CPU core.
    Works with all monitoring modes.

    Parameters
    ----------
    color_map: str
        The name of the matplotlib colormap to use for coloring different application instances.
        See https://matplotlib.org/stable/tutorials/colors/colormaps.html for available colormaps.
    """

    def __init__(self, color_map: str = "CMRmap") -> None:
        self._color_map = plt.get_cmap(color_map)

    @property
    def clip_filename(self) -> str:
        return "app_mapping_plot"
    
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
        
        # Load data
        trace_provider = result_wrapper.get_trace_provider()
        instance_to_affinity_ranges = self._get_instance_affinity_ranges(trace_provider)
        
        # Calculate colors and positions
        cmap = self._color_map
        instance_ids = [iid for iids in trace_provider.get_app_index().values() for iid in iids]
        instance_to_color = {iid: cmap(i / len(instance_ids)) for i, iid in enumerate(instance_ids)}
        utilized_cores = sorted({core for ranges in instance_to_affinity_ranges.values() for core in ranges.keys()})
        core_to_y = {core: -i for i, core in enumerate(utilized_cores)}

        # Create figure
        fig_width = 8
        fig_height = max(5, len(utilized_cores) * 0.5)
        fig, ax = plt.subplots(figsize=(fig_width, fig_height), layout='constrained')

        # Plot bars for each instance's affinity ranges
        for app_name, instances in trace_provider.get_app_index().items():
            app_name = app_name.replace("splash2x.", "").replace("parsec.","").replace("-1","")
            for iid in instances:
                if iid not in instance_to_affinity_ranges:
                    continue
                
                affinity_ranges = instance_to_affinity_ranges[iid]
                bar_color = instance_to_color[iid]
                label = f"{app_name} ({iid})" if len(instances) > 1 else app_name

                label_once = label  # To only label the first bar for the legend
                for core, time_ranges in affinity_ranges.items():
                    for start, end in time_ranges:
                        ax.barh(
                            y=core_to_y[core], width=end - start, left=start,
                            color=bar_color, height=0.8,
                            label=label_once
                        )
                        label_once = None

        # Decorate plot
        ax.set_yticks([core_to_y[core] for core in utilized_cores])
        ax.set_yticklabels([f"Core {core}" for core in utilized_cores])
        ax.set_xlabel("Time (s)")
        ax.grid(axis='y', linestyle='--', alpha=0.5)
        ax.set_axisbelow(True)

        # Adjust legend based on number of instances
        legend_columns = min(3, len(instance_ids))
        ax.legend(loc='lower center', bbox_to_anchor=(0.5, 1), ncol=legend_columns)

        return fig

    def _get_instance_affinity_ranges(self, trace_provider: TraceProvider) -> dict[int, dict[int, list[tuple[float, float]]]]:
        instance_to_affinity_ranges: dict[int, dict[int, list[tuple[float, float]]]] = defaultdict(dict)
        for _, instance_ids in trace_provider.get_app_index().items():
            for iid in instance_ids:
                timestamps, affinity = trace_provider.get_affinity_trace(iid)
                affinity_index_ranges = self.find_number_ranges(affinity) # type: ignore
                # Map indexed affinity ranges to timestamp ranges
                affinity_timestamp_ranges = {
                    core: [(timestamps[start], timestamps[min(end + 1, len(timestamps) - 1)]) 
                           for start, end in ranges] 
                           for core, ranges in affinity_index_ranges.items()
                }
                instance_to_affinity_ranges[iid] = affinity_timestamp_ranges

        return instance_to_affinity_ranges  
    
    def find_number_ranges(self, list_of_sets: list[set[int]]) -> dict[int, list[tuple[int, int]]]:
        """
        Finds the contiguous ranges for each number in a list of sets.

        >>>Example:
            Input: [{1, 2}, {1, 2}, {2}, {3}, {3}, {1, 3}]
            Output: {
                1: [(0, 1), (5, 5)],
                2: [(0, 2)],
                3: [(3, 4), (5, 5)]
            }
        """
        result: dict[int, list[tuple[int, int]]] = {}

        for index, current_set in enumerate(list_of_sets):
            for number in current_set:
                # Check if this is the first occurrence of the number
                if number not in result:
                    result[number] = [(index, index)]
                else:
                    last_start, last_end = result[number][-1]
                    # Check if the current index continues the last range
                    if index == last_end + 1:
                        result[number][-1] = (last_start, index)
                    # Otherwise, start a new range
                    else:
                        result[number].append((index, index))
        return result
    