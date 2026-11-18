# T-014 evidence scripts

The T-014 report and images are in [docs/evaluation/characters/T-014](../../characters/T-014/README.md). These two
one-off scripts were moved here from `pipeline/clips/` by T-072 (one-off evidence scripts belong with their task
evidence; audit T-069 §2.7, item C6):

- `make_t014_shot.py`: writes an untracked T-010 derivative shot whose boy cast entry uses the unpublished T-014
  1.1.0 spec override (`python3 docs/evaluation/animation/T-014/make_t014_shot.py --out <file>`).
- `t014_contact_sheet.py`: the frames 30–60 boy-eye contact strip from that render.

Only `make_t014_shot.py`'s repository-root computation changed (two more `..` for the new folder depth); the output
is the same.
