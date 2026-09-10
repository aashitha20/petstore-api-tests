# Petstore uploadImage API — Automated Tests

Automated test suite for `POST /pet/{petId}/uploadImage` on the Swagger
Petstore demo API (https://petstore.swagger.io/).

## Files
- `test_upload_image.py` — pytest test cases (positive, negative, edge, response-quality checks)
- `requirements.txt` — Python dependencies
- `.github/workflows/daily-api-tests.yml` — GitHub Actions workflow that runs the suite every day at 6 AM UTC and uploads an HTML report

## Run locally

```bash
pip install -r requirements.txt
pytest test_upload_image.py -v --html=report.html --self-contained-html
```

Open `report.html` in a browser to see results.

## Run daily automatically (GitHub Actions)

1. Push this folder to a GitHub repository (keep the `.github/workflows/` folder as-is).
2. Go to the repo's **Actions** tab — the workflow "Daily Petstore API Tests" will appear.
3. It runs automatically every day at 06:00 UTC, and you can also trigger it manually via **Run workflow**.
4. Each run's HTML report is saved as a downloadable artifact under that run, for 30 days.

## Run daily automatically (cron, no GitHub needed)

On Linux/Mac, edit your crontab:
```bash
crontab -e
```
Add:
```
0 6 * * * cd /path/to/petstore_tests && pytest test_upload_image.py -v --html=report.html --self-contained-html
```

On Windows, use Task Scheduler to run the same `pytest` command daily.

## What's covered

- Valid upload with/without metadata
- Invalid/negative/non-numeric petId
- Empty file upload
- Wrong file type (no image validation check)
- Script/XSS content in metadata field
- Response time and Content-Type header checks

See inline comments in `test_upload_image.py` — several negative tests
intentionally assert a *range* of acceptable status codes (e.g. `(200, 404)`)
because this is a public demo server with loose validation. Where the actual
result differs from ideal API behavior, that's the basis for a bug/finding
in your test report, not a broken test.
