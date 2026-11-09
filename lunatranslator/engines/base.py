from abc import ABC, abstractmethod

class TranslationEngine(ABC):
    name = "Base"

    @abstractmethod
    def translate(self, text, source, target):
        raise NotImplementedError
