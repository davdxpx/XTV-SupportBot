from xtv_support.core.container import Container
from xtv_support.services.external_directory.factory import build_default_directory_provider
from xtv_support.services.external_directory.model import DirectoryProviderLike
from xtv_support.services.external_directory.null_provider import NullDirectoryProvider

def test_build_default_directory_provider_registers():
    container = Container()
    container.register(DirectoryProviderLike, build_default_directory_provider)

    provider = container.resolve(DirectoryProviderLike)

    assert isinstance(provider, NullDirectoryProvider)
