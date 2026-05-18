"""
Accès Azure Key Vault via Service Principal.

AZURE_TENANT_ID et AZURE_CLIENT_ID  : lus depuis .env (identifiants, non secrets)
AZURE_CLIENT_SECRET                 : lu depuis l'environnement du processus OU
                                      directement dans le registre Windows (HKLM puis HKCU)
                                      — jamais stocké dans un fichier.
"""
import os
import winreg
from functools import lru_cache
from azure.identity import ClientSecretCredential
from azure.keyvault.secrets import SecretClient

VAULT_URL = os.getenv("AZURE_KEYVAULT_URL", "https://sifa-vault1.vault.azure.net/")


def _read_registry(name: str) -> str:
    """Lit une variable d'environnement depuis le registre Windows (HKLM puis HKCU)."""
    for hive, subkey in [
        (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
        (winreg.HKEY_CURRENT_USER,  r"Environment"),
    ]:
        try:
            key = winreg.OpenKey(hive, subkey)
            value, _ = winreg.QueryValueEx(key, name)
            winreg.CloseKey(key)
            if value:
                return value
        except OSError:
            pass
    return ""


def _get_sp_secret() -> str:
    """Retourne AZURE_CLIENT_SECRET depuis l'env du processus ou le registre Windows."""
    return os.getenv("AZURE_CLIENT_SECRET") or _read_registry("AZURE_CLIENT_SECRET")


@lru_cache(maxsize=1)
def _client() -> SecretClient:
    tenant_id   = os.getenv("AZURE_TENANT_ID",  "")
    client_id   = os.getenv("AZURE_CLIENT_ID",  "")
    client_sec  = _get_sp_secret()

    if not all([tenant_id, client_id, client_sec]):
        missing = [k for k, v in {
            "AZURE_TENANT_ID":     tenant_id,
            "AZURE_CLIENT_ID":     client_id,
            "AZURE_CLIENT_SECRET": client_sec,
        }.items() if not v]
        raise EnvironmentError(f"Credentials SP manquants : {', '.join(missing)}")

    credential = ClientSecretCredential(
        tenant_id=tenant_id,
        client_id=client_id,
        client_secret=client_sec,
    )
    return SecretClient(vault_url=VAULT_URL, credential=credential)


def get_secret(name: str) -> str:
    return _client().get_secret(name).value
