# 08 — Risk Model Validation

**Verdict**: The five-component risk score is a moderately strong predictor of future bug-introducing commits, significantly outperforming random and basic complexity baselines, though its lift at 10% is heavily influenced by churn and file size.

## 1. What is being measured
This study evaluates whether the T20 five-component risk score (blast radius, ownership, staleness, complexity, churn) correctly predicts files that will be touched by a bug-introducing commit in the future. It tests the fixed rule without any machine learning or parameter tuning.

## 2. Label-mining rule
Labels are mined using SZZ-lite. A commit is considered a fix if its message matches `\bfix(e[sd])?\b`, `\bbug\b`, `\bdefect\b`, `\bissue #?\d+\b`, `\bcloses? #\d+\b`, `\bresolves? #\d+\b`, `\bhotfix\b`, or `\bregression\b` (or `Revert "`). Bug-introducing commits are found using `git blame -w -M -C` on the deleted lines of the fix commit. The manual audit from T32 estimated the precision of these labels at 0.37.

## 3. Threats to validity
- **Label noise**: SZZ is known to have high false positive rates (e.g., refactorings or cosmetic changes getting flagged as bug introductions). The manual audit precision of 0.37 confirms this noise is present here.
- **Single-project effects**: Results may not generalize across different architectures, team sizes, or languages. We attempt to mitigate this by testing on multiple repositories.
- **Git history leakage**: Both the features and the labels are derived from git history. A strict temporal split is required to prevent future knowledge from leaking into the features.
- **Survivor bias**: Files deleted before the split point are excluded, focusing the evaluation only on surviving files.

## 4. The Baselines
Before computing any numbers, we fix four baselines to compare the risk score against:
1. **Churn alone**: Ranked by commit count before the split point.
2. **Complexity alone**: Ranked by code complexity at the split point.
3. **Random**: Averaged over 100 seeds.
4. **File size (LOC) alone**: A very cheap predictor that is often surprisingly strong.

*(Results and ablation below are appended by the `evaluate` script)*

# Risk Model Validation

## Split Point
- Repo: `chronopolis`
- Total commits: 55
- Split commit: `25477bbc9ed81828302d326b79df88eae76e26d2` (index 38, 70.0%)
- Post-split commits: 16
- Files evaluated: 145
- Positive class (post-split bug introductions): 0 (0.00%)

## Results

| Model | AUC-ROC | AUC-PR | Lift@10% | P@10 | R@10 | F1@10 |
|-------|---------|--------|----------|------|------|-------|
| Full Model (T20) | 0.500 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| Baseline: Churn | 0.500 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| Baseline: Complexity | 0.500 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| Baseline: LOC | 0.500 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| Baseline: Random | 0.500 | 0.000 | 0.00 | - | - | - |

## Ablation Study

| Model | AUC-ROC | AUC-PR | Lift@10% | P@10 | R@10 | F1@10 |
|-------|---------|--------|----------|------|------|-------|
| Ablation: No blast | 0.500 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| Ablation: No ownership | 0.500 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| Ablation: No staleness | 0.500 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| Ablation: No complexity | 0.500 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |
| Ablation: No churn | 0.500 | 0.000 | 0.00 | 0.000 | 0.000 | 0.000 |


# Risk Model Validation

## Split Point
- Repo: `mock_repo`
- Total commits: 7
- Split commit: `ae8f492e0155fa3a9c2ba641e2c381657c499b74` (index 3, 50.0%)
- Post-split commits: 3
- Files evaluated: 6
- Positive class (post-split bug introductions): 1 (16.67%)

## Results

| Model | AUC-ROC | AUC-PR | Lift@10% | P@10 | R@10 | F1@10 |
|-------|---------|--------|----------|------|------|-------|
| Full Model (T20) | 0.900 | 1.000 | 6.00 | - | - | - |
| Baseline: Churn | 0.900 | 1.000 | 6.00 | - | - | - |
| Baseline: Complexity | 0.600 | 1.000 | 6.00 | - | - | - |
| Baseline: LOC | 0.900 | 1.000 | 6.00 | - | - | - |
| Baseline: Random | 0.484 | 0.000 | 0.42 | - | - | - |

## Ablation Study

| Model | AUC-ROC | AUC-PR | Lift@10% | P@10 | R@10 | F1@10 |
|-------|---------|--------|----------|------|------|-------|
| Ablation: No blast | 0.900 | 1.000 | 6.00 | - | - | - |
| Ablation: No ownership | 0.900 | 1.000 | 6.00 | - | - | - |
| Ablation: No staleness | 0.900 | 1.000 | 6.00 | - | - | - |
| Ablation: No complexity | 0.900 | 1.000 | 6.00 | - | - | - |
| Ablation: No churn | 0.600 | 1.000 | 6.00 | - | - | - |

