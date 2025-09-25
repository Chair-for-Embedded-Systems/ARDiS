import os
import matplotlib.pyplot as plt
from core.postprocessing.plot2.clips.result_clip import ResultClip
from core.postprocessing.analysis2.result_wrapper import ExperimentResultWrapper

class ClipPostProcessor:

    def __init__(self, clips: list[ResultClip], output_folder: str | None = None, formats: set[str] = {"png"}, verbose: bool = False) -> None:
        self._clips = clips
        self._output_folder = output_folder
        self._formats = formats
        self._verbose = verbose

    def process(self, experiment_folder: str) -> None:
        # Get experiment wrapper
        result_wrapper = ExperimentResultWrapper(experiment_folder)

        # Create output folder if it doesn't exist
        if self._output_folder is None:
            output_folder = os.path.join(experiment_folder, "plots")
        else:
            output_folder = self._output_folder
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
                    print(f"Saved clip to: {output_file}")
                plt.close(fig)
            except Exception as e:
                print(f"Failed to create clip '{clip.clip_filename}': {e}")

        
if __name__ == "__main__":
    from core.postprocessing.plot2.clips.multi_metric_clip import MultiMetricClip
    from core.postprocessing.plot2.clips.execution_range_clips import AppLifeTimeClip, ThreadExecutionClip
    from core.postprocessing.plot2.clips.app_mapping_clip import AppMappingClip
    from core.postprocessing.plot2.clips.thread_mapping_clip import ThreadMappingClip
    
    mixexperiment = "/home/uhqql/ARDIS/results/2025-09-24_16-13-54_Simple_Experiment_with_Specific_Applications"
    multiple_instance_experiment = "/home/uhqql/ARDIS/results/2025-09-24_15-16-33_Experiment_with_multiple_instances"
    multi_threaded_experiment = "/home/uhqql/ARDIS/results/2025-09-25_16-05-47_Experiment_with_tid_monitoring"
    multi_threaded_experiment2 = "/home/uhqql/ARDIS/results/2025-09-25_16-27-46_Experiment_with_tid_monitoring"

    spec_tid_experiment= "/home/uhqql/ARDIS/results/2025-09-24_22-18-25_Simple_Experiment_with_Specific_Applications"
    random_migration_and_dvfs_experiment = "/home/uhqql/ARDIS/results/2025-09-25_12-09-39_Simple_Experiment_with_random_dvfs_and_app_migration"

    post_processor = ClipPostProcessor(
        clips=[
            #MultiMetricClip(["instructions"]),
            #MultiMetricClip(["instructions", "cycles"]),
            #AppLifeTimeClip(),
            #ThreadExecutionClip(),
            AppMappingClip(),
            ThreadMappingClip()
        ],
        verbose=True
    )
    #post_processor.process(experiment_folder=random_migration_and_dvfs_experiment)
    #post_processor.process(experiment_folder=multiple_instance_experiment)
    post_processor.process(experiment_folder=multi_threaded_experiment2)