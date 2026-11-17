# Testing

Run protocol tests from the repository root:

```bash
source .venv/bin/activate
python -m unittest discover -s tests -p 'test_*.py' -v
```

Use `test_execution_template.csv` to record actual observations. Leave a case Pending until it has been executed and evidence saved. Do not mark PASS based only on code inspection.
