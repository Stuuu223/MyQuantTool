from logic.logger import logger
from .base import ICapitalFlowProvider
from .level1_provider import Level1InferenceProvider

class DataProviderFactory:
    _instances = {}

    @staticmethod
    def create(provider_type: str = 'level1') -> ICapitalFlowProvider:
        if provider_type in DataProviderFactory._instances:
            return DataProviderFactory._instances[provider_type]

        provider = None
        if provider_type == 'level1':
            provider = Level1InferenceProvider()
        else:
            logger.warning(f"Unknown provider type: {provider_type}, falling back to Level1")
            provider = Level1InferenceProvider()

        DataProviderFactory._instances[provider_type] = provider
        return provider

def get_provider(provider_type: str = 'level1') -> ICapitalFlowProvider:
    return DataProviderFactory.create(provider_type)