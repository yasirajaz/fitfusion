# FitFusion

Streamlit + MySQL fitness tracker: profile targets, weekly workout plan, food log, progress and adaptive calories.

## Quick start
1. `pip install -r requirements.txt`
2. As MySQL root, run both files in order:
   ```
   mysql -u root -p < schema.sql
   mysql -u root -p < setup_user.sql
   ```
   (to wipe an OLD-format database first: `DROP DATABASE fitfusion;`)
3. `streamlit run app.py` from this folder.

The app logs in as `fitfusion_user` / `fit1234` by default. To use another login, set
`FITFUSION_DB_USER`, `FITFUSION_DB_PASSWORD`, `FITFUSION_DB_HOST`, `FITFUSION_DB_PORT`,
`FITFUSION_DB_NAME`, or copy `.streamlit/secrets.toml.example` to `.streamlit/secrets.toml`.
**Upgrading from the previous version** (keeps your users, weights and food logs):
```
mysql -u root -p < migrate_v2.sql
mysql -u root -p < schema.sql
```

Optional: `FITFUSION_TZ` sets the timezone for "today" (default `Asia/Kolkata`).
Tests: `pytest tests`

## Layout
- `app.py` UI only · `repository.py` all SQL · `db.py` pooled, safe connections
- `migrate_v2.sql` upgrade script · `setup_user.sql` creates the DB login
- `calculations.py` pure formulas · `workout.py` plan generator · `schema.sql` database
