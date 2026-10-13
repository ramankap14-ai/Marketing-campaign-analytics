"""Step 1: clean raw data, engineer features, load into SQLite."""
import sqlite3
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data/raw/marketing_campaign.csv"
DB = ROOT / "data/campaign.db"
REF_DATE = pd.Timestamp("2014-07-01")  # day after the last customer signup in the file

df = pd.read_csv(RAW, sep=";", encoding="utf-8-sig")
n0 = len(df)
log = {}

# --- Cleaning decisions (each one is documented in the README) ---
log["missing_income"] = int(df["Income"].isna().sum())
df = df.dropna(subset=["Income"])

log["income_outlier"] = int((df["Income"] > 200_000).sum())   # one row at 666,666
df = df[df["Income"] <= 200_000]

df["Dt_Customer"] = pd.to_datetime(df["Dt_Customer"])
df["age"] = REF_DATE.year - df["Year_Birth"]
log["impossible_age"] = int((df["age"] > 90).sum())            # born 1893/1899/1900
df = df[df["age"] <= 90]

df["Marital_Status"] = df["Marital_Status"].replace({"Alone": "Single"})
log["junk_marital"] = int(df["Marital_Status"].isin(["Absurd", "YOLO"]).sum())
df = df[~df["Marital_Status"].isin(["Absurd", "YOLO"])]

# --- Feature engineering ---
mnt = [c for c in df.columns if c.startswith("Mnt")]
df["total_spend"] = df[mnt].sum(axis=1)
df["wine_share"] = df["MntWines"] / df["total_spend"]
df["total_purchases"] = df[["NumWebPurchases", "NumCatalogPurchases", "NumStorePurchases"]].sum(axis=1)
df["deal_share"] = (df["NumDealsPurchases"] / df["total_purchases"].where(df["total_purchases"] > 0)).fillna(0).clip(upper=1)
df["children"] = df["Kidhome"] + df["Teenhome"]
df["tenure_days"] = (REF_DATE - df["Dt_Customer"]).dt.days
cmp_cols = [f"AcceptedCmp{i}" for i in range(1, 6)]
df["prior_accepted"] = df[cmp_cols].sum(axis=1)

df["income_band"] = pd.qcut(df["Income"], 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"]).astype(str)
df["spend_band"] = pd.qcut(df["total_spend"], 4, labels=["Q1 (lowest)", "Q2", "Q3", "Q4 (highest)"]).astype(str)

df = df.rename(columns={"Response": "response", "ID": "customer_id", "Education": "education",
                        "Marital_Status": "marital_status", "Income": "income",
                        "Recency": "recency_days", "Complain": "complain"})
keep = ["customer_id", "age", "education", "marital_status", "income", "children", "Kidhome", "Teenhome",
        "tenure_days", "recency_days", "total_spend", "wine_share", "total_purchases", "deal_share",
        "NumWebVisitsMonth", "NumDealsPurchases", "prior_accepted", "complain",
        "income_band", "spend_band", "response"] + cmp_cols + mnt
df = df[keep]

df.to_csv(ROOT / "data/processed/customers_clean.csv", index=False)
with sqlite3.connect(DB) as con:
    df.to_sql("customers", con, if_exists="replace", index=False)

print(f"raw rows: {n0} -> clean rows: {len(df)} (dropped {n0 - len(df)})")
print("drops:", log)
print(f"overall response rate: {df['response'].mean():.2%}")
