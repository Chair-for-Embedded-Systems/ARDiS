from abc import ABC, abstractmethod
from typing import Any
from matplotlib.figure import Figure
from core.postprocessing.analysis2.result_wrapper import ExperimentResultWrapper

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