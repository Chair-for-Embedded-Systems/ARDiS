import os
import matplotlib.pyplot as plt
from core.postprocessing.clips.result_clip import ResultClip
from core.postprocessing.analysis.result_wrapper import ExperimentResultWrapper
from core.postprocessing.postprocessor import PostProcessor

class ClipPostProcessor(PostProcessor):
    """
    Post-processor that generates plots using specified ResultClip instances.
    Parameters
    ----------
    clips: list[ResultClip]
        List of ResultClip instances to use for generating plots.
    output_folder: str | None
        Folder where the generated plots will be saved. If None, the default folder (plots folder in experiment) will be used.
    formats: set[str]
        Set of file formats to save the plots (e.g., {"png", "pdf"}).
    verbose: bool
        If True, additional information will be printed during processing.
    """

    def __init__(self, clips: list[ResultClip], output_folder: str | None = None, formats: set[str] = {"png"}, verbose: bool = False) -> None:
        self._clips = clips
        self._output_folder = output_folder
        self._formats = formats
        self._verbose = verbose

    def process(self, experiment_folder: str) -> None:
        # Get experiment wrapper
        result_wrapper = ExperimentResultWrapper(experiment_folder)
        
        # Create output folder if not exists
        output_folder = self._output_folder or os.path.join(experiment_folder, "plots")
        os.makedirs(output_folder, exist_ok=True)

        for clip in self._clips:
            try:
                with plt.style.context(clip.style or {}):
                    fig = clip.create_plot(result_wrapper)
                    output_file = os.path.join(output_folder, f"{clip.clip_filename}.png")
                    # Save in all specified formats
                    for fmt in self._formats:
                        output_file = os.path.join(output_folder, f"{clip.clip_filename}.{fmt}")
                        fig.savefig(output_file, bbox_inches='tight', dpi=300)
                
                if self._verbose:
                    print(f"[Clip-Postprocessor] Saved clip to: {output_file}")
                plt.close(fig)
            except Exception as e:
                print(f"[Clip-Postprocessor] Failed to create clip '{clip.clip_filename}': {e}")
