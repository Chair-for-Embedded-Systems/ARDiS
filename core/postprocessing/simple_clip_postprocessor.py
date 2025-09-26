from enum import Enum
from .clip_postprocessor import ClipPostProcessor
from .clips import *

class Clips(Enum):
        APP_EXECUTION_OVERVIEW = 1
        APP_MAPPING = 2
        APP_METRICS_ALL = 3
        THREAD_MAPPING = 4
        THREAD_EXECUTION_OVERVIEW = 5
        SYSTEM_METRICS_ALL = 6
        SYSTEM_CORE_FREQUENCY = 7

class SimpleClipPostProcessor(ClipPostProcessor):
        
    """
    A wrapper around ClipPostProcessor that allows selection from a predefined set of common clips.
    For further customization, use ClipPostProcessor directly.

    Parameters
    ----------
    output_folder: str | None
        Folder where the generated plots will be saved. If None, the default folder (plots folder in experiment) will be used.
    formats: set[str]
        Set of file formats to save the plots (e.g., {"png", "pdf"}).
    verbose: bool
        If True, additional information will be printed during processing.
    """
    def __init__(self, clips: list[Clips], output_folder: str | None = None, formats: set[str] = {"png"}, verbose: bool = False) -> None:
        
        clip_instances: list[ResultClip] = []

        for clip in clips:
            if clip == Clips.APP_EXECUTION_OVERVIEW:
                clip_instances.append(AppExecutionClip())
            
            elif clip == Clips.APP_MAPPING:
                clip_instances.append(AppMappingClip())
            
            elif clip == Clips.APP_METRICS_ALL:
                clip_instances.append(AppMultiMetricClip())
            
            elif clip == Clips.THREAD_MAPPING: 
                clip_instances.append(ThreadMappingClip())
            
            elif clip == Clips.THREAD_EXECUTION_OVERVIEW:
                clip_instances.append(ThreadExecutionClip())
            
            elif clip == Clips.SYSTEM_METRICS_ALL:
                clip_instances.append(SystemMetricClip())

            elif clip == Clips.SYSTEM_CORE_FREQUENCY:
                clip_instances.append(SystemFrequencyClip())
                            
            else:
                raise ValueError(f"Unknown clip type: {clip}")

        super().__init__(clips=clip_instances, output_folder=output_folder, formats=formats, verbose=verbose)