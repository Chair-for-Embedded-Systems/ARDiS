import os
from enum import Enum
from .analysis.experiment_analyser import ExperimentAnalyser
from .plot.plot_metric_by_time import plot_app_metric_by_time
from .plot.plot_mapping_by_time import plot_apps_by_mapped_core

class ResultPlotter():
    def __init__(self, output_folder: str):
       os.makedirs(output_folder, exist_ok=True)
       self.output_folder = output_folder

    def plot_results(self, verbose: bool = False):
        """
        Plots the result.

        Parameters
        ----------
        verbose: bool
            Specifies if the plot generation should be verbose (print output_file to console). Defaults to False
        """
        raise NotImplementedError()        


class Diagrams(Enum):
    FREQUENCY = 0
    INSTRUCTIONS = 1
    LLC_LOADS = 2
    LLC_LOAD_MISSES = 3
    LLC_STORES = 4
    LLC_STORE_MISSES = 5
    CYCLES = 6
    BRACNHES = 7
    BRANCH_MISSES = 8
    ENERGY_USAGE = 9
    MAPPING = 10

class BasicResultPlotter(ResultPlotter):
    def __init__(self, 
                 experiment_folder: str, 
                 output_folder: str | None = None, 
                 diagrams: list[Diagrams] = [diagram for diagram in Diagrams],
                 aoi: str | None = None):
        
        """
        Initialize a basic ReslutPlotter that plots various metrics of the experiment that is given by it folder.
        
        Parameters
        ----------
        experiment_folder: str | None
            Specifies the experiment folder which provides the data for the diagrams. 
        output_folder : str | None
            Specifies the output folder for the diagrams. 
            Defaults to `./plots` of the given experiment_folder.
        diagrams : list[Diagrams]
            Specifies the diagrams that should be plotted. Defaults to all diagrams.
        aoi : str | None
            Specifies an application of interest. If set the diagrams will only contain the data of the aoi.
        """
          
        super().__init__(output_folder if output_folder else os.path.join(experiment_folder, "plots"))

        self.__experiment_folder = experiment_folder
        self.__diagrams = diagrams
        self.__aoi = aoi

    def plot_results(self, verbose: bool = False):
        
        experiment = ExperimentAnalyser(self.__experiment_folder)
        
        applications = experiment.get_applications()

        # Apply aoi filter if necessary
        if self.__aoi:
            if self.__aoi in applications:
                applications = [self.__aoi]
            else:
                raise Exception(f"{self.__aoi} is not present in {self.__experiment_folder}")

        of = self.output_folder

        TIME_LABEL = "Seconds (s)"

        if Diagrams.FREQUENCY in self.__diagrams:
            data = {app: experiment.get_frequency_series(app) for app in applications}
            plot_app_metric_by_time(
                output_file=os.path.join(of, "frequency.png"),
                data=data,
                title="Frequency of different apps",
                x_label=TIME_LABEL,
                y_label="Frequency (MHz)",
                verbose=verbose
            )

        if Diagrams.INSTRUCTIONS in self.__diagrams:
            data = {app: experiment.get_instruction_series(app) for app in applications}
            plot_app_metric_by_time(
                output_file=os.path.join(of, "instructions.png"),
                data=data,
                title="Instructions of different apps",
                x_label=TIME_LABEL,
                y_label="Instructions (Millions)",
                y_unit_size=1e6,
                verbose=verbose
            )

        if Diagrams.LLC_LOADS in self.__diagrams:
            data = {app: experiment.get_llc_load_series(app) for app in applications}
            plot_app_metric_by_time(
                output_file=os.path.join(of, "llc_loads.png"),
                data=data,
                title="LLC-loads of different apps",
                x_label=TIME_LABEL,
                y_label="LLC-loads",
                verbose=verbose
            )

        if Diagrams.LLC_LOAD_MISSES in self.__diagrams:
            data = {app: experiment.get_llc_load_misses_series(app) for app in applications}
            plot_app_metric_by_time(
                output_file=os.path.join(of, "llc_load_misses.png"),
                data=data,
                title="LLC-load-misses of different apps",
                x_label=TIME_LABEL,
                y_label="LLC-load-misses",
                verbose=verbose
            )

        if Diagrams.LLC_STORES in self.__diagrams:
            data = {app: experiment.get_llc_store_series(app) for app in applications}
            plot_app_metric_by_time(
                output_file=os.path.join(of, "llc_store.png"),
                data=data,
                title="LLC-store of different apps",
                x_label=TIME_LABEL,
                y_label="LLC-store",
                verbose=verbose
            )

        if Diagrams.LLC_STORE_MISSES in self.__diagrams:
            data = {app: experiment.get_llc_store_misses_series(app) for app in applications}
            plot_app_metric_by_time(
                output_file=os.path.join(of, "llc_store_misses.png"),
                data=data,
                title="LLC-store-misses of different apps",
                x_label=TIME_LABEL,
                y_label="LLC-store-misses",
                verbose=verbose
            )

        if Diagrams.CYCLES in self.__diagrams:
            data = {app: experiment.get_cycle_series(app) for app in applications}
            plot_app_metric_by_time(
                output_file=os.path.join(of, "cycles.png"),
                data=data,
                title="Cycles of different apps",
                x_label=TIME_LABEL,
                y_label="Cycles (Millions)",
                y_unit_size=1e6,
                verbose=verbose
            )

        if Diagrams.BRANCH_MISSES in self.__diagrams:
            data = {app: experiment.get_branch_misses_series(app) for app in applications}
            plot_app_metric_by_time(
                output_file=os.path.join(of, "branch_misses.png"),
                data=data,
                title="Branch misses of different apps",
                x_label=TIME_LABEL,
                y_label="Branch misses",
                verbose=verbose
            )

        if Diagrams.BRACNHES in self.__diagrams:
            data = {app: experiment.get_branch_series(app) for app in applications}
            plot_app_metric_by_time(
                output_file=os.path.join(of, "branches.png"),
                data=data,
                title="Branches of different apps",
                x_label=TIME_LABEL,
                y_label="Branches",
                verbose=verbose
            )
        
        if Diagrams.ENERGY_USAGE in self.__diagrams:
            data = {
                "Energy_Cores" : experiment.get_energy_core_series(),
                "Energy_Package" : experiment.get_energy_package_series(),
                "Energy_System" : experiment.get_energy_system_series(),
            }
            plot_app_metric_by_time(
                output_file=os.path.join(of, "energy_usage.png"),
                data=data,
                title="Energy usage different apps",
                x_label=TIME_LABEL,
                y_label="Energy (J)",
                verbose=verbose
            )
        
        if Diagrams.MAPPING in self.__diagrams:
            plot_apps_by_mapped_core(
                output_file=os.path.join(of, "mapping.png"),
                data={app : experiment.get_core_mapping_intervalls(app) for app in applications},
                verbose=verbose
            )
  