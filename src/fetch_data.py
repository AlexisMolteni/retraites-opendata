import sys
import requests
import pandas as pd
import os
from dotenv import load_dotenv

load_dotenv()

# Force UTF-8 output sur Windows (console cp1252)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_URL = os.getenv("BASE_URL", "https://data.assuranceretraite.fr/api/explore/v2.1/catalog/datasets")
RAW_DIR = os.getenv("DATA_RAW_DIR", "data/raw")


def list_datasets() -> list[dict]:
    r = requests.get(f"{BASE_URL}?limit=50&lang=fr", timeout=30)
    r.raise_for_status()
    return r.json()["results"]


def fetch_dataset(dataset_id: str, page_size: int = 100) -> pd.DataFrame:
    all_records = []
    offset = 0
    while True:
        url = f"{BASE_URL}/{dataset_id}/records?limit={page_size}&offset={offset}&lang=fr"
        r = requests.get(url, timeout=60)
        r.raise_for_status()
        data = r.json()
        records = data.get("results", [])
        all_records.extend(records)
        total = data.get("total_count", len(all_records))
        if len(all_records) >= total or not records:
            break
        offset += page_size
    return pd.DataFrame(all_records)


def download_all(output_dir: str = RAW_DIR) -> None:
    os.makedirs(output_dir, exist_ok=True)
    datasets = list_datasets()
    print(f"{len(datasets)} datasets trouves.")
    errors = []
    for ds in datasets:
        ds_id = ds["dataset_id"]
        print(f"Telechargement : {ds_id}")
        try:
            df = fetch_dataset(ds_id)
            out_path = os.path.join(output_dir, f"{ds_id}.parquet")
            df.to_parquet(out_path, index=False)
            print(f"  OK {len(df)} enregistrements -> {out_path}")
        except Exception as exc:
            print(f"  ERREUR {ds_id} : {exc}")
            errors.append((ds_id, str(exc)))
    if errors:
        print(f"\n{len(errors)} dataset(s) en erreur :")
        for ds_id, msg in errors:
            print(f"  - {ds_id} : {msg}")


if __name__ == "__main__":
    download_all()
