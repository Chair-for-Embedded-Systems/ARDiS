from abc import ABC, abstractmethod
from core.postprocessing.analysis2.result_wrapper import ExperimentResultWrapper

class ResultPlotter(ABC):

    @abstractmethod
    def plot_results(self, expertiment_folder: str, output_folder: str | None = None):
        """
        Abstract method to plot results. Must be implemented by subclasses.

        Parameters
        ----------
        expertiment_folder : str
            Path to the folder containing experiment data.
        output_folder : str | None
            Path to the folder where output plots will be saved.
        """
        pass

    def _load_results(self, expertiment_folder: str) -> ExperimentResultWrapper:
        return ExperimentResultWrapper(experiment_folder=expertiment_folder)
    