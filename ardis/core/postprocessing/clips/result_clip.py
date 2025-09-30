from abc import ABC, abstractmethod
from typing import Any
from matplotlib.figure import Figure
from ardis.core.postprocessing.analysis.result_wrapper import ExperimentResultWrapper

class ResultClip(ABC):

    @abstractmethod
    def create_plot(self, result_wrapper: ExperimentResultWrapper) -> Figure:
        pass

    @property
    @abstractmethod
    def clip_filename(self) -> str:
        """Filename (without extension) for saving the clip."""
        raise NotImplementedError()

    @property
    def style(self) -> dict[str, Any] | None:
        """Optional style dictionary for matplotlib styling."""
        return None

class ResultClipUtils:
    @staticmethod
    def strip_application_label(app_label: str) -> str:
        """Strips common prefixes from application labels for cleaner display."""
        prefixes = ['parsec.', 'splash2x.', 'spec2006.', 'spec2006-']
        short_app_label = app_label
        for prefix in prefixes:
            short_app_label = short_app_label.removeprefix(prefix)
        return short_app_label