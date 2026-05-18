import pandas as pd
import os
from pathlib import Path

RAW_DIR = "data/raw"
PROCESSED_DIR = "data/processed"


def load_raw(dataset_id: str) -> pd.DataFrame:
    path = Path(RAW_DIR) / f"{dataset_id}.parquet"
    return pd.read_parquet(path)


def save_processed(df: pd.DataFrame, dataset_id: str) -> None:
    os.makedirs(PROCESSED_DIR, exist_ok=True)
    path = Path(PROCESSED_DIR) / f"{dataset_id}.parquet"
    df.to_parquet(path, index=False)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = (
        df.columns.str.lower()
        .str.replace(" ", "_")
        .str.replace(r"[^\w]", "_", regex=True)
    )
    return df


def cast_numeric_columns(df: pd.DataFrame) -> pd.DataFrame:
    for col in df.columns:
        try:
            df[col] = pd.to_numeric(df[col])
        except (ValueError, TypeError):
            pass
    return df


def clean_dataset(dataset_id: str) -> pd.DataFrame:
    df = load_raw(dataset_id)
    df = normalize_columns(df)
    df = cast_numeric_columns(df)
    df = df.drop_duplicates()
    save_processed(df, dataset_id)
    print(f"{dataset_id} → {len(df)} lignes, {df.shape[1]} colonnes")
    return df


def clean_all() -> None:
    for parquet_file in Path(RAW_DIR).glob("*.parquet"):
        clean_dataset(parquet_file.stem)


if __name__ == "__main__":
    clean_all()
