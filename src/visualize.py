"""Fonctions de visualisation réutilisables (matplotlib + plotly)."""
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path

REPORTS_DIR = Path("reports")
sns.set_theme(style="whitegrid", palette="muted")


def save_fig(fig, name: str, subdir: str = "") -> Path:
    out = REPORTS_DIR / subdir
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"{name}.png"
    fig.savefig(path, dpi=150, bbox_inches="tight")
    return path


def plot_time_series(series: pd.Series, title: str = "", ylabel: str = "", save_as: str = "") -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(series.index, series.values, marker="o", linewidth=2)
    ax.set_title(title, fontsize=13)
    ax.set_ylabel(ylabel)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x, _: f"{x:,.0f}"))
    plt.tight_layout()
    if save_as:
        save_fig(fig, save_as)
    return fig


def plot_forecast(historical: pd.Series, forecast: pd.Series, title: str = "", save_as: str = "") -> plt.Figure:
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.plot(historical.index, historical.values, label="Historique", marker="o")
    ax.plot(forecast.index, forecast.values, label="Prévision", linestyle="--", marker="x", color="tomato")
    ax.axvline(x=historical.index[-1], color="gray", linestyle=":")
    ax.set_title(title, fontsize=13)
    ax.legend()
    plt.tight_layout()
    if save_as:
        save_fig(fig, save_as)
    return fig


def plot_gender_gap(df: pd.DataFrame, year_col: str, male_col: str, female_col: str, title: str = "") -> go.Figure:
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df[year_col], y=df[male_col], name="Hommes", mode="lines+markers"))
    fig.add_trace(go.Scatter(x=df[year_col], y=df[female_col], name="Femmes", mode="lines+markers"))
    fig.update_layout(title=title, xaxis_title="Année", yaxis_title="Montant (€)", template="plotly_white")
    return fig


def plot_carsat_map(df: pd.DataFrame, region_col: str, value_col: str, title: str = "") -> px.Figure:
    fig = px.bar(df.sort_values(value_col, ascending=True), x=value_col, y=region_col,
                 orientation="h", title=title, template="plotly_white")
    return fig
