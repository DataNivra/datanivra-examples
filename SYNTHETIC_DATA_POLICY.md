# Synthetic data policy

Everything in this repository that looks like data is **synthetic**: invented by a generator or
written by hand for the example. Nothing here was copied, sampled or derived from production
systems, customers, patients, employees or any real person or organisation.

## Rules for every contribution

1. **Synthetic only.** Never add real personal data, customer data, health or financial records,
   production extracts, logs or screenshots of real systems -- not even "anonymised" or masked
   copies. Masked production data is still derived from real people.
2. **Declare data files.** Every data file (`.csv`, `.json` fixtures, `.sql` seeds, ...) lives in a
   directory covered by a `SYNTHETIC_MANIFEST.json` naming the generator, the seed and a short
   description. CI fails when a data file has no manifest
   (`.github/scripts/check_synthetic_data.py`).
3. **Use reserved values.** E-mail addresses use reserved domains (`example.com`, `example.org`,
   `*.invalid`, `*.test`); identifiers are random or sequential, never real account, card,
   social-security or health-plan numbers.
4. **No secrets.** Credentials appear only as references (`vault://...`, `k8s://...`, `env://...`)
   or as `<PLACEHOLDER>` values. CI runs a secret scanner on every pull request.

If you find something in this repository that looks real, report it privately
([SECURITY.md](SECURITY.md)); we remove it and rewrite history where necessary.
