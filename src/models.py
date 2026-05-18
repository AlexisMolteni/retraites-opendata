"""
Modèles prédictifs : ARIMA, Prophet, régression linéaire.
Usage : importer les fonctions dans les notebooks ou en CLI.
"""
import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error


# ── ARIMA ────────────────────────────────────────────────────────────────────

def fit_arima(series: pd.Series, order: tuple = (1, 1, 1)):
    model = ARIMA(series, order=order)
    return model.fit()


def forecast_arima(series: pd.Series, steps: int = 5, order: tuple = (1, 1, 1)) -> pd.Series:
    result = fit_arima(series, order)
    forecast = result.forecast(steps=steps)
    last_idx = series.index[-1]
    future_idx = range(last_idx + 1, last_idx + steps + 1) if isinstance(last_idx, int) else None
    return pd.Series(forecast.values, index=future_idx, name="forecast")


# ── Prophet ──────────────────────────────────────────────────────────────────

def forecast_prophet(df: pd.DataFrame, periods: int = 5, freq: str = "Y") -> pd.DataFrame:
    """df doit avoir des colonnes 'ds' (datetime) et 'y' (valeur)."""
    try:
        from prophet import Prophet
    except ImportError:
        raise ImportError("Installer prophet : pip install prophet")
    m = Prophet(yearly_seasonality=True)
    m.fit(df)
    future = m.make_future_dataframe(periods=periods, freq=freq)
    forecast = m.predict(future)
    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]


# ── Régression linéaire ───────────────────────────────────────────────────────

def fit_linear(X: pd.DataFrame, y: pd.Series) -> LinearRegression:
    model = LinearRegression()
    model.fit(X, y)
    return model


def evaluate(y_true, y_pred) -> dict:
    return {
        "mae": mean_absolute_error(y_true, y_pred),
        "rmse": np.sqrt(mean_squared_error(y_true, y_pred)),
    }
