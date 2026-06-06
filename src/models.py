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
    last_idx_int = int(last_idx) if isinstance(last_idx, (int, np.integer)) else None
    future_idx = range(last_idx_int + 1, last_idx_int + steps + 1) if last_idx_int is not None else None
    return pd.Series(forecast.values, index=future_idx, name="forecast")


# ── Prophet ──────────────────────────────────────────────────────────────────

def forecast_prophet(df: pd.DataFrame, periods: int = 5, freq: str = "Y",
                     changepoints: list = None) -> pd.DataFrame:
    """df doit avoir des colonnes 'ds' (datetime) et 'y' (valeur)."""
    try:
        from prophet import Prophet
    except ImportError:
        raise ImportError("Installer prophet : pip install prophet")
    kwargs = {"yearly_seasonality": True}
    if changepoints:
        kwargs["changepoints"] = [pd.Timestamp(c) for c in changepoints
                                   if pd.Timestamp(c) <= df["ds"].max()]
    m = Prophet(**kwargs)
    m.fit(df)
    future = m.make_future_dataframe(periods=periods, freq=freq)
    forecast = m.predict(future)
    return forecast[["ds", "yhat", "yhat_lower", "yhat_upper"]]


# ── Régression linéaire ───────────────────────────────────────────────────────

def fit_linear(X: pd.Series, y: pd.Series):
    """Retourne (model, mae, rmse)."""
    model = LinearRegression()
    X_arr = X.values.reshape(-1, 1)
    model.fit(X_arr, y)
    y_pred = model.predict(X_arr)
    mae = mean_absolute_error(y, y_pred)
    rmse = np.sqrt(mean_squared_error(y, y_pred))
    return model, mae, rmse


def evaluate(y_true, y_pred) -> tuple:
    """Retourne (mae, rmse)."""
    mae = mean_absolute_error(y_true, y_pred)
    rmse = np.sqrt(mean_squared_error(y_true, y_pred))
    return mae, rmse
