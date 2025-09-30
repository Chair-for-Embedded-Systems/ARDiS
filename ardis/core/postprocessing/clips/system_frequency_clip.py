from typing import Any
from matplotlib import pyplot as plt

from ardis.core.postprocessing.clips.result_clip import ResultClip, ExperimentResultWrapper, Figure
from ardis.core.postprocessing.analysis.trace_provider import TraceProvider

class SystemFrequencyClip(ResultClip):
    """
    This clip creates a line plot showing the frequency of specified CPU cores over time.
    
    **Warning**: The frequency of a core is only logged when an application thread is running on it.
    If no application is running on a core, its frequency will not be recorded, leading to
    potential gaps in the plot.
    
    Parameters
    ----------
    cores: set[int] | None
        A set of core IDs to include in the plot. If None, all cores are included.
    use_scatter: bool
        If True, use scatter plot instead of line plot. Default is False.
        This is useful if the underlying data is sparse (e.g due to an active migration policy).
    skip_unavailable_cores: bool
        If True, skip cores that are not available in the trace data without raising an error.
    frequency_range_mhz: tuple[float, float]
        The frequency range (min, max) to display on the y-axis. If None, the default range will be used.
    color_map: str
        The name of the matplotlib colormap to use for coloring different CPU cores.
        See https://matplotlib.org/stable/tutorials/colors/colormaps.html for available colormaps.
    """
    def __init__(
        self,
        cores: set[int] | None = None,
        use_scatter: bool = False,
        skip_unavailable_cores: bool = False,
        frequency_range_mhz: tuple[float, float] | None = (700, 5200),
        color_map: str = "CMRmap"
    ) -> None:
        if cores and len(cores) == 0:
            raise ValueError("Cores set must not be empty.")
        self._cores = cores
        self._use_scatter = use_scatter
        self._skip_unavailable_cores = skip_unavailable_cores
        self._frequency_range = frequency_range_mhz
        self._color_map = plt.get_cmap(color_map)

    @property
    def clip_filename(self) -> str:
        return "system_frequency_plot"

    @property
    def style(self) -> dict[str, Any] | None:
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

        # Get trace provider
        trace_provider: TraceProvider = result_wrapper.get_trace_provider()
        core_to_freq = trace_provider.get_core_frequency_traces()

        # Check if specified cores are available
        if self._cores:
            unavailable_cores = self._cores - core_to_freq.keys()
            if not self._skip_unavailable_cores and unavailable_cores:
                raise ValueError(
                    f"Specified cores {unavailable_cores} are not available in the trace data. "
                    f"Available cores: {list(core_to_freq.keys())}"
                )

        # Create color lookup for each core
        cmap = self._color_map
        core_ids = core_to_freq.keys() if not self._cores else self._cores & core_to_freq.keys()
        core_to_color = {core: cmap(i / len(core_ids)) for i, core in enumerate(sorted(core_ids))}

        fig, axes = plt.subplots(figsize=(6, 4), layout='constrained')
        for core_id, freq_trace in sorted(core_to_freq.items()):            
            if self._cores and core_id not in self._cores:
                continue
            time, freq = freq_trace
            color = core_to_color[core_id]
            if self._use_scatter:
                axes.scatter(time, freq, label=f"Core {core_id}", alpha=0.7, s=10, color=color)
            else:
                axes.plot(time, freq, label=f"Core {core_id}", color=color)

        axes.set_xlabel("Time (s)")
        axes.set_ylabel("Frequency (MHz)")
        axes.grid(True, axis='both', which='both', linestyle='-', linewidth=0.8, color='#000', alpha=0.2)
        axes.set_axisbelow(True)

        if self._frequency_range:
            axes.set_ylim(bottom=self._frequency_range[0], top=self._frequency_range[1])

        handles, labels = axes.get_legend_handles_labels()
        axes.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 1), ncol=5)

        return fig
