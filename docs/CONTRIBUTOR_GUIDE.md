# Contributor guide
First contribution: improve a synthetic example, add a validation edge-case test, improve screen
reader wording in the future UI, or clarify a documented calculation. Comment on a labeled issue
with the small scope you intend to address. A good-first-issue label is not permission to skip review.

Use meaningful commit messages and focused diffs. A rule PR states formula, input cohort, unknown
handling, numerator/denominator, limitations, false-positive explanations and verification steps.
A source PR states access limits, rights evidence, attribution, privacy minimization and mapping
coverage. Extension requirements are in [EXTENSIONS](EXTENSIONS.md).

No auto-execution of contributor URLs or notebooks, no confidential data in CI, and no statistical
claim without reproducible fixtures. Add sample output when useful, label synthetic material, and
consider accessible tables instead of unexplained risk colors. Corrections/disputes and conflicts
follow [governance](../GOVERNANCE.md). Maintainer reviews behavior, security, evidence and docs.
