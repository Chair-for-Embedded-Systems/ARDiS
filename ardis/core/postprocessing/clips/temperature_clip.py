from typing import Any
from matplotlib import pyplot as plt
from matplotlib.axes import Axes

from ardis.core.postprocessing.clips.result_clip import ResultClip, ExperimentResultWrapper, Figure
from ardis.core.postprocessing.analysis.trace_provider import TraceProvider

class TemperatureClip(ResultClip):
    """
    This clip creates a line plot for core temperatures over time.
    Parameters
    ----------
    cores: set[int]
        A set of core IDs to plot temperatures for. If None, all available cores will be plotted.
    """

    def __init__(
        self,
        cores: set[int] | None = None,
        color_map: str = "CMRmap"
    ) -> None:
        super().__init__()
        self._selected_cores = cores
        self._color_map = plt.get_cmap(color_map)

    @property
    def clip_filename(self) -> str:
        return "core_temperature_plot"

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
        core_temp_traces = trace_provider.get_core_temp_traces()

        if self._selected_cores is not None:
            core_temp_traces = {
                core_id: traces 
                for core_id, traces in core_temp_traces.items() if core_id in self._selected_cores
            }

        # Create unique colors for each core
        cmap = self._color_map
        core_to_color = {
            core: cmap(i / len(core_temp_traces.keys())) 
            for i, core in enumerate(sorted(core_temp_traces.keys()))
        }

        fig, axes = plt.subplots(figsize=(9, 6), constrained_layout=True)

        # Plot temperature for each core over time
        for core_id, (timestamps, temperatures) in sorted(core_temp_traces.items()):
            axes.plot(timestamps, temperatures, label=f"Core {core_id}", color=core_to_color[core_id])

        axes.set_xlabel("Time (s)")
        axes.set_ylabel("Temperature (°C)")
        axes.grid(True, axis='both', which='both', linestyle='-', linewidth=0.8, color='#000', alpha=0.2)
        axes.set_axisbelow(True)

        handles, labels = axes.get_legend_handles_labels()

        axes.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 1), ncol=4)
        return fig