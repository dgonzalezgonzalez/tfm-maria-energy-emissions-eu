# Repository Guidelines

## Project Structure & Module Organization
- `scripts/`: executable logic (`fetch_process_plot_emissions.py`).
- `data/raw/`: unmodified Eurostat download.
- `data/processed/`: cleaned CSV outputs.
- `output/figures/`: generated charts.
- `docs/plans/`: planning notes.
- `README.md`: project summary + method.

Do not mix raw, processed, and figure artifacts.

## Build, Test, and Development Commands
- `python3 scripts/fetch_process_plot_emissions.py`: full pipeline (raw JSON -> processed CSVs -> PNG).
- `python3 -m py_compile scripts/fetch_process_plot_emissions.py`: syntax check.
- `git status -b`: verify branch and staged/unstaged changes.
- Optional venv: `python3 -m venv .venv && .venv/bin/python scripts/fetch_process_plot_emissions.py`.

## Coding Style & Naming Conventions
- Python 3, 4-space indentation, small helper functions.
- Prefer standard library unless dependency adds clear value.
- Use descriptive `snake_case` file names.
- Keep dataset names explicit (`source + geo + sector`), e.g. `eurostat_env_air_gge_es_eu27_crf1.json`.

## Testing Guidelines
- No formal test framework yet.
- After changes, run pipeline and verify:
  - expected files regenerated,
  - base year index is `1.000000` for `ES` and `EU27_2020`,
  - chart renders without errors.
- Add reproducibility checks for new logic (row counts, year range, schema assertions).

## Commit & Pull Request Guidelines
- Use concise imperative commits (e.g., `Add Eurostat processing script`).
- Keep commits scoped (script logic, data refresh, docs).
- Keep remote updated: after each completed change, run `git add`, `git commit`, and `git push`.
- PRs should state scope, source/parameter changes, output impact, and updated chart preview when figure changes.

## Agent Communication Mode
- Default mode: use `$caveman wenyan-ultra` ALWAYS.
- Exception: if user must clearly understand a direct ask or final process summary, switch to `$caveman` only.
- After clarity-critical message, return to `$caveman wenyan-ultra`.
