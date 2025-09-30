import os
import shutil
import matplotlib.pyplot as plt
from timeit import default_timer as timer
from ardis.core.postprocessing.clips.result_clip import ResultClip
from ardis.core.postprocessing.analysis.result_wrapper import ExperimentResultWrapper
from ardis.core.postprocessing.postprocessor import PostProcessor

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
    skip_latex_check: bool
        If True, skip the check for LaTeX installation (useful for false negatives).
    """

    def __init__(self, clips: list[ResultClip], output_folder: str | None = None, formats: set[str] = {"png"}, verbose: bool = False, skip_latex_check: bool = False) -> None:
        self._clips = clips
        self._output_folder = output_folder
        self._formats = formats
        self._verbose = verbose
        self._skip_latex_check = skip_latex_check

    def process(self, experiment_folder: str) -> None:
        # Get experiment wrapper
        result_wrapper = ExperimentResultWrapper(experiment_folder)
        
        # Create output folder if not exists
        output_folder = self._output_folder or os.path.join(experiment_folder, "plots")
        os.makedirs(output_folder, exist_ok=True)
        self._log(f"Generating clips in: {output_folder}")
        start_time = timer()

        # Check if a LaTeX installation is available
        if self._skip_latex_check:
            latex_installed = True
        else:
            latex_installed = self._check_latex_installed()
            self._log(f"LaTeX detected: {latex_installed}")

        for clip in self._clips:
            try:
                # Check if LaTeX is required and installed
                clip_style = clip.style or {}
                if clip_style.get("text.usetex", False) and not latex_installed:
                    # Override to disable LaTeX if not installed
                    clip_style["text.usetex"] = False
                    self._log(f"Warning: LaTeX is not installed. Disabling LaTeX for clip '{clip.clip_filename}'.")

                with plt.style.context(clip_style):
                    fig = clip.create_plot(result_wrapper)
                    output_file = os.path.join(output_folder, f"{clip.clip_filename}.png")
                    # Save in all specified formats
                    for fmt in self._formats:
                        output_file = os.path.join(output_folder, f"{clip.clip_filename}.{fmt}")
                        fig.savefig(output_file, bbox_inches='tight', dpi=300)
                        self._log(f"Saved clip to: {output_file}")

                plt.close(fig)
            except Exception as e:
                print(f"[Clip-Postprocessor] Failed to create clip '{clip.clip_filename}': {e}")

        self._log(f"Finished generating clips in {timer() - start_time:.2f} seconds.")

    def _log(self, message: str) -> None:
        if self._verbose:
            print(f"[Clip-Postprocessor] {message}")

    def _check_latex_installed(self) -> bool:
        """Check if LaTeX is installed on the system."""
        try:
            return shutil.which("latex") is not None
        except FileNotFoundError:
            return False
