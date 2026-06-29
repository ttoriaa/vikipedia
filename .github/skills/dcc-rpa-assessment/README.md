# dcc-rpa-assessment

## Purpose
Generate a merged CSV that preserves DCC classification columns and appends row-level processing behavior fields.

## Package Contents
- `SKILL.md`: Copilot routing contract.
- `README.md`: local setup and usage notes.
- `UAT.md`: manual acceptance scenario.
- `UAT.meta.json`: machine-readable UAT metadata.
- `scripts/run_dcc_rpa_assessment.py`: local execution skeleton.

## Local Usage
Run the skeleton in dry-run mode:

```powershell
./.venv/Scripts/python.exe ./.github/skills/dcc-rpa-assessment/scripts/run_dcc_rpa_assessment.py --source <confluence-url> --dry-run
```

## Notes
- This local package provides a starting point only.
- Domain logic for DCC extraction and CSV generation still needs to be implemented against your real source material.
