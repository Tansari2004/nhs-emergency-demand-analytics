# Original fixed-fit evaluation

These two exports preserve the original experiment: fit the forest through
August 2024, hold its parameters fixed, and update lag inputs with observed
prior months across September 2024-August 2026. The original `.pbix`, PDF and
report screenshots use these results: seasonal MAE 9,874.21 and fixed-fit forest
MAE 15,501.42 admissions/month.

The current `powerbi/data/` exports add monthly expanding-window refits, retain
the fixed-fit predictions as a comparison, and publish the training cutoff and
training row count for every target. The original files are retained for
provenance, not presented as the new model's results.
