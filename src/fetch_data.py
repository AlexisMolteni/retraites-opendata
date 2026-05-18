import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("BASE_URL", "https://data.assuranceretraite.fr/api/explore/v2.1/catalog/datasets")
RAW_DIR = os.getenv("DATA_RAW_DIR", "data/raw")


def list_datasets() -> list[dict]:
    r = requests.get(f"{BASE_URL}?limit=50&lang=fr", timeout=30)
    r.raise_for_status()
    return r.json()["results"]


def fetch_dataset(dataset_id: str, limit: int = 10000) -> pd.DataFrame:
    url = f"{BASE_URL}/{dataset_id}/records?limit={limit}&lang=fr"
    r = requests.get(url, timeout=60)
    r.raise_for_status()
    records = r.json()["results"]
    return pd.DataFrame(records)


def download_all(output_dir: str = RAW_DIR) -> None:
    os.makedirs(output_dir, exist_ok=True)
    datasets = list_datasets()
    print(f"{len(datasets)} datasets trouvés.")
    for ds in datasets:
        ds_id = ds["dataset_id"]
        print(f"Téléchargement : {ds_id}")
        try:
            df = fetch_dataset(ds_id)
            out_path = os.path.join(output_dir, f"{ds_id}.parquet")
            df.to_parquet(out_path, index=False)
            print(f"  → {len(df)} enregistrements  →  {out_path}")
        except Exception as exc:
            print(f"  ✗ Erreur pour {ds_id} : {exc}")


if __name__ == "__main__":
    download_all()
