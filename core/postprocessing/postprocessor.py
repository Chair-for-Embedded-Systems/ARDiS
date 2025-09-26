from abc import ABC, abstractmethod

class PostProcessor(ABC):
    @abstractmethod
    def process(self, experiment_folder: str) -> None:
        pass