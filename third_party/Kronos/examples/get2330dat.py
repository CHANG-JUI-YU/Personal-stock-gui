import yfinance as yf

df = yf.download(
    "2330.TW",
    period="2y",
    auto_adjust=True
)

# 修正 MultiIndex
if hasattr(df.columns, "nlevels") and df.columns.nlevels > 1:
    df.columns = df.columns.get_level_values(0)

df = df.reset_index()

df = df.rename(columns={
    "Date": "timestamps",
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume"
})

df["amount"] = df["close"] * df["volume"]

df = df[
    [
        "timestamps",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "amount"
    ]
]

print(df.head())

df.to_csv(
    "2330_tw.csv",
    index=False
)