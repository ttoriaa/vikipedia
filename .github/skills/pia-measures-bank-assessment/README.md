# pia-measures-bank-assessment

## Purpose
Transform feature evidence into a final Measures Bank V4.0 assessment package in English.

## Package Contents
- `SKILL.md`
- `README.md`
- `UAT.md`
- `UAT.meta.json`
- `measures_bank_assessment_snapshot.json`
- `scripts/run_pia_measures_bank_assessment.py`

## Local Usage

```powershell
./.venv/Scripts/python.exe ./.github/skills/pia-measures-bank-assessment/scripts/run_pia_measures_bank_assessment.py --source <feature-page> --snapshot ./.github/skills/pia-measures-bank-assessment/measures_bank_assessment_snapshot.json --dry-run
```

## Notes
- The included snapshot is a placeholder and must be replaced with a reviewed local copy before real use.
