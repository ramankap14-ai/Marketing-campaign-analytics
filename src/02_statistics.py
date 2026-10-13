"""Step 2: statistical tests on who responds to the last campaign."""
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parents[1]
df = pd.read_csv(ROOT / "data/processed/customers_clean.csv")
rows = []

def cramers_v(ct):
    chi2 = stats.chi2_contingency(ct, correction=False)[0]
    n = ct.values.sum()
    return np.sqrt(chi2 / (n * (min(ct.shape) - 1)))

# 1) Categorical / binary predictors vs response: chi-square + Cramer's V
df["any_prior_accept"] = (df["prior_accepted"] > 0).astype(int)
df["has_children"] = (df["children"] > 0).astype(int)
for col in ["any_prior_accept", "education", "marital_status", "has_children", "complain"]:
    ct = pd.crosstab(df[col], df["response"])
    chi2, p, dof, _ = stats.chi2_contingency(ct)
    rows.append({"test": "chi-square", "variable": col, "statistic": chi2, "p_value": p,
                 "effect_size": cramers_v(ct), "effect_metric": "Cramer's V"})

# 2) Continuous predictors: responders vs non-responders (Mann-Whitney, skewed data)
for col in ["income", "total_spend", "recency_days", "age", "tenure_days", "NumWebVisitsMonth", "deal_share"]:
    a = df.loc[df.response == 1, col]; b = df.loc[df.response == 0, col]
    u, p = stats.mannwhitneyu(a, b, alternative="two-sided")
    rows.append({"test": "mann-whitney", "variable": col, "statistic": u, "p_value": p,
                 "effect_size": u / (len(a) * len(b)), "effect_metric": "P(responder > non-responder)"})

res = pd.DataFrame(rows)
m = len(res)
res["p_bonferroni"] = (res["p_value"] * m).clip(upper=1)   # 12 tests -> correct for multiple comparisons
res["significant_at_5pct"] = res["p_bonferroni"] < 0.05
res = res.round(4)
res.to_csv(ROOT / "outputs/statistical_tests.csv", index=False)
print(res.to_string(index=False))

# 3) Bootstrap CI: response-rate gap between prior acceptors and everyone else
rng = np.random.default_rng(42)
g1 = df.loc[df.any_prior_accept == 1, "response"].values
g0 = df.loc[df.any_prior_accept == 0, "response"].values
diffs = [rng.choice(g1, len(g1)).mean() - rng.choice(g0, len(g0)).mean() for _ in range(5000)]
lo, hi = np.percentile(diffs, [2.5, 97.5])
print(f"\nPrior acceptors: {g1.mean():.1%} (n={len(g1)}) vs never accepted: {g0.mean():.1%} (n={len(g0)})")
print(f"Gap = {g1.mean()-g0.mean():.1%}, 95% bootstrap CI [{lo:.1%}, {hi:.1%}]")

# 4) Does the income effect survive once spend is controlled for? (partial check via stratification)
df["spend_tier"] = pd.qcut(df["total_spend"], 3, labels=["low", "mid", "high"])
df["income_hi"] = (df["income"] > df["income"].median()).astype(int)
print("\nResponse rate by income (above/below median) within spend tier:")
print(df.groupby(["spend_tier", "income_hi"], observed=True)["response"].agg(["mean", "count"]).round(3))
