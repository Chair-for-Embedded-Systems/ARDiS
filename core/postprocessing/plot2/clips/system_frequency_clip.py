from typing import Any
from matplotlib import pyplot as plt

from core.postprocessing.plot2.clips.result_clip import ResultClip, ExperimentResultWrapper, Figure
from core.postprocessing.analysis2.trace_provider import TraceProvider

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
    """
    def __init__(self, cores: set[int] | None = None) -> None:
        if cores and len(cores) == 0:
            raise ValueError("Cores set must not be empty.")
        self._cores = cores

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
            'legend.fontsize': 16,
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
            if unavailable_cores:
                raise ValueError(
                    f"Specified cores {unavailable_cores} are not available in the trace data. "
                    f"Available cores: {list(core_to_freq.keys())}"
                )

        fig, axes = plt.subplots(figsize=(6, 4), constrained_layout=True)
        for core_id, freq_trace in sorted(core_to_freq.items()):            
            if self._cores and core_id not in self._cores:
                continue
            time, freq = freq_trace
            axes.plot(time, freq, label=f"Core {core_id}", alpha=0.7)

        axes.set_xlabel("Time (s)")
        axes.set_ylabel("Frequency (MHz)")
        axes.grid(True, axis='both', which='both', linestyle='-', linewidth=0.8, color='#000', alpha=0.2)
        
        handles, labels = axes.get_legend_handles_labels()
        fig.legend(handles, labels, loc="lower center", bbox_to_anchor=(0.5, 1), ncol=5)

        return fig
