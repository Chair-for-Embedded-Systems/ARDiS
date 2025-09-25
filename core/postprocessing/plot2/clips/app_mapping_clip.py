from typing import Any
from unittest import result
from matplotlib.axes import Axes 
from matplotlib import pyplot as plt

from core.postprocessing.plot2.clips.result_clip import ResultClip, ExperimentResultWrapper, Figure
from core.postprocessing.analysis2.trace_provider import TraceProvider, PeriodicLog

class AppMappingClip(ResultClip):
    """
    Clip that visualizes the mapping of applications to CPU cores over time.
    """

    def __init__(self, color_map: str | None = "CMRmap") -> None:
        self._color_map = plt.get_cmap(color_map)

    @property
    def clip_filename(self) -> str:
        return "app_mapping_plot"
    
    @property
    def style(self) -> dict[str, Any] | None:
        return {
            'text.usetex': True,
            'font.family': 'serif',
            'axes.labelsize': 12,
            'axes.titlesize': 14,
            'legend.fontsize': 12,
            'xtick.labelsize': 10,
            'ytick.labelsize': 10
        }

    def create_plot(self, result_wrapper: ExperimentResultWrapper) -> Figure:
        
        # Load data
        trace_provider = result_wrapper.get_trace_provider()
        instance_to_affinity_ranges = self._get_affinity(result_wrapper.get_periodic_log())
        
        # Calculate colors and positions
        cmap = self._color_map
        instance_ids = [iid for iids in trace_provider.get_app_index().values() for iid in iids]
        instance_to_color = {iid: cmap(i / len(instance_ids)) for i, iid in enumerate(instance_ids)}
        utilized_cores = sorted({core for ranges in instance_to_affinity_ranges.values() for core in ranges.keys()})
        core_to_y = {core: -i for i, core in enumerate(utilized_cores)}

        fig_width = 6
        fig_height = min(4, len(utilized_cores) * 0.35)
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        for app_name, instances in trace_provider.get_app_index().items():
            for iid in instances:
                if iid not in instance_to_affinity_ranges:
                    continue
                affinity_ranges = instance_to_affinity_ranges[iid]
                
                label = f"{app_name} (ID {iid})" if len(instances) > 1 else app_name

                label_once = label  # To only label the first bar for the legend
                for core, time_ranges in affinity_ranges.items():
                    for start, end in time_ranges:
                        ax.barh(
                            core_to_y[core],
                            end - start,
                            left=start,
                            color=instance_to_color[iid],
                            height=0.8,
                            label=label_once
                        )
                        label_once = None

        ax.set_yticks([core_to_y[core] for core in utilized_cores])
        ax.set_yticklabels([f"Core {core}" for core in utilized_cores])
        ax.grid(axis='y', linestyle='--', alpha=0.5)
        ax.set_axisbelow(True)
        ax.legend(loc='upper center', bbox_to_anchor=(0.5, 1.15), ncol=len(instance_ids))
        ax.set_xlabel("Time (s)")

        return fig
    
    def _get_affinity(self, periodic_log: PeriodicLog) -> dict[int, dict[int, list[tuple[float, float]]]]:

        iid_to_affinity: dict[int, list[tuple[float, set[int]]]] = {}
        for app_event in periodic_log.app_events:
            if app_event.instance_id not in iid_to_affinity:
                iid_to_affinity[app_event.instance_id] = []

            iid_to_affinity[app_event.instance_id].append((app_event.timestamp_sec, app_event.affinity))

        intance_to_affinity_ranges: dict[int, dict[int, list[tuple[float, float]]]] = {}

        for iid, timestamp_and_affinity in iid_to_affinity.items():
            timestamps = [t for t, _ in timestamp_and_affinity]
            afflist = [a for _, a in timestamp_and_affinity]
            affinity_index_ranges = self.find_number_ranges(afflist)
            # Map indexed affinity ranges to timestamp ranges
            affinity_timestamp_ranges = {
                core: [(timestamps[start], timestamps[min(end + 1, len(timestamps) - 1)]) for start, end in ranges] for core, ranges in affinity_index_ranges.items()
            }
            intance_to_affinity_ranges[iid] = affinity_timestamp_ranges
        
        return intance_to_affinity_ranges

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
        

if __name__ == "__main__":
    clip = AppMappingClip()
    exp_pl = ExperimentResultWrapper("/home/uhqql/ARDIS/results/2025-09-25_10-33-29_Simple_Experiment_with_random_dvfs_and_app_migration")
    clip._get_affinity(exp_pl.get_periodic_log())
    #ranges = clip.find_number_ranges([{1,2}, {1,2}, {2}, {3}, {3}, {1, 3}])
    #print(ranges)
    #clip.create_plot(exp_pl)