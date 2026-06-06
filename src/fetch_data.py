"""Accès à l'API OpenDataSoft d'Assurance Retraite."""
import os
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://data.assuranceretraite.fr/api/explore/v2.1/catalog/datasets")


def list_datasets() -> list[dict]:
    resp = requests.get(f"{BASE_URL}?limit=100", timeout=30)
    resp.raise_for_status()
    return resp.json().get("results", [])


def fetch_dataset(dataset_id: str, limit: int = 10_000) -> pd.DataFrame:
    resp = requests.get(
        f"{BASE_URL}/{dataset_id}/records",
        params={"limit": limit},
        timeout=60,
    )
    resp.raise_for_status()
    records = resp.json().get("results", [])
    return pd.DataFrame(records)
