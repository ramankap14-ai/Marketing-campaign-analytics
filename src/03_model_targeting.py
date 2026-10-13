"""Step 3: propensity model, out-of-fold scoring, decile lift, targeting ROI."""
import sqlite3
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "data/campaign.db"
CHARTS = ROOT / "outputs/charts"
COST, REV = 3, 11            # per-contact cost / revenue per responder (dataset constants Z_CostContact, Z_Revenue)

df = pd.read_csv(ROOT / "data/processed/customers_clean.csv")
num = ["age", "income", "children", "tenure_days", "recency_days", "total_spend", "wine_share",
       "total_purchases", "deal_share", "NumWebVisitsMonth", "prior_accepted", "complain"]
cat = ["education", "marital_status"]
X, y = df[num + cat], df["response"]

prep = ColumnTransformer([("num", StandardScaler(), num),
                          ("cat", OneHotEncoder(drop="first"), cat)])
logit = Pipeline([("prep", prep), ("m", LogisticRegression(max_iter=2000))])
gbm = Pipeline([("prep", prep), ("m", GradientBoostingClassifier(random_state=42, max_depth=2, n_estimators=150, learning_rate=0.05))])

cv = StratifiedKFold(5, shuffle=True, random_state=42)
oof = {}
for name, model in [("logistic", logit), ("gradient_boosting", gbm)]:
    oof[name] = cross_val_predict(model, X, y, cv=cv, method="predict_proba")[:, 1]
    print(f"{name:18s} 5-fold out-of-fold AUC = {roc_auc_score(y, oof[name]):.3f}")

# Naive baseline: rank customers by 'prior_accepted' alone
print(f"{'prior_accepted only':18s} AUC = {roc_auc_score(y, df['prior_accepted'] + 1e-6 * df['total_spend']):.3f}")

# Use logistic regression: near-equal accuracy, and every coefficient is explainable to a business partner.
df["score"] = oof["logistic"]

# Odds ratios from the final fit (per +1 SD for numeric features)
logit.fit(X, y)
names = num + list(logit.named_steps["prep"].named_transformers_["cat"].get_feature_names_out(cat))
coefs = pd.DataFrame({"feature": names, "odds_ratio": np.exp(logit.named_steps["m"].coef_[0])})
coefs["odds_ratio"] = coefs["odds_ratio"].round(2)
coefs = coefs.sort_values("odds_ratio", ascending=False)
coefs.to_csv(ROOT / "outputs/model_odds_ratios.csv", index=False)
print("\nOdds ratios (per +1 SD for numeric features):\n", coefs.to_string(index=False))

# Write scores to SQLite so the SQL lift/ROI queries can use them
with sqlite3.connect(DB) as con:
    df[["customer_id", "score"]].to_sql("scores", con, if_exists="replace", index=False)
    lift = pd.read_sql_query((ROOT / "sql/02_decile_lift.sql").read_text(), con)
    roi = pd.read_sql_query((ROOT / "sql/03_roi_by_depth.sql").read_text(), con)

print("\nDecile lift:\n", lift.to_string(index=False))
print("\nProfit by targeting depth:\n", roi.to_string(index=False))
n, r = len(df), int(df["response"].sum())
print(f"\nContact everyone: {n} contacts, {r} responders, profit = {r*REV - n*COST}")
best = roi.loc[roi["profit"].idxmax()]
print(f"Best depth: top {int(best.top_n_deciles_contacted)} deciles -> profit {int(best.profit)}, "
      f"{int(best.contacts)} contacts, {int(best.responders)} responders")

# --- Charts ---
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False})
seg = df.groupby("prior_accepted")["response"].agg(["mean", "count"]).reset_index()
fig, ax = plt.subplots(figsize=(6, 3.6))
bars = ax.bar(seg["prior_accepted"].astype(str), seg["mean"] * 100, color="#1f4e79")
ax.axhline(COST / REV * 100, color="#c0392b", ls="--", lw=1.2, label="Break-even (27.3%)")
for b, c in zip(bars, seg["count"]):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.5, f"n={c}", ha="center", fontsize=8)
ax.set_xlabel("Previous campaigns accepted"); ax.set_ylabel("Response rate to last campaign (%)")
ax.set_title("Past behaviour is the strongest predictor"); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(CHARTS / "response_by_prior_campaigns.png", dpi=160); plt.close(fig)

fig, ax = plt.subplots(figsize=(6, 3.6))
ax.bar(lift["decile"].astype(str), lift["response_rate_pct"], color="#1f4e79")
ax.axhline(COST / REV * 100, color="#c0392b", ls="--", lw=1.2, label="Break-even (27.3%)")
ax.axhline(df["response"].mean() * 100, color="grey", ls=":", lw=1.2, label="Overall average")
ax.set_xlabel("Model score decile (1 = most likely to respond)"); ax.set_ylabel("Response rate (%)")
ax.set_title("Decile response rate"); ax.legend(frameon=False)
fig.tight_layout(); fig.savefig(CHARTS / "decile_response_rate.png", dpi=160); plt.close(fig)

fig, ax = plt.subplots(figsize=(6, 3.6))
ax.plot(roi["top_n_deciles_contacted"], roi["profit"], marker="o", color="#1f4e79")
ax.axhline(0, color="black", lw=0.8)
ax.set_xlabel("Deciles contacted (best first)"); ax.set_ylabel("Profit (revenue 11 - cost 3 per contact)")
ax.set_title("Contact fewer, earn more"); ax.set_xticks(range(1, 11))
fig.tight_layout(); fig.savefig(CHARTS / "profit_by_targeting_depth.png", dpi=160); plt.close(fig)
