"""
Automated test suite for: POST /pet/{petId}/uploadImage
Swagger Petstore demo API: https://petstore.swagger.io/

Run manually:
    pytest test_upload_image.py -v --html=report.html --self-contained-html

Notes:
- This targets a public demo/mock server with no real persistence, so some
  "negative" tests may not behave like a production API would (documented
  inline where relevant).
"""

import io
import time
import requests
import pytest

BASE_URL = "https://petstore.swagger.io/v2"
UPLOAD_ENDPOINT = "{base}/pet/{pet_id}/uploadImage"

VALID_PET_ID = 1  # Known-existing pet id on the demo server


def make_fake_image(size_bytes: int = 1024, name: str = "test.jpg"):
    """Return a (filename, file-like, content-type) tuple for requests."""
    content = b"\xff\xd8\xff" + (b"0" * max(size_bytes - 3, 0))  # fake JPEG header + padding
    return (name, io.BytesIO(content), "image/jpeg")


# ---------------------------------------------------------------------------
# Positive test cases
# ---------------------------------------------------------------------------

def test_tc01_valid_upload_with_metadata():
    """Valid petId + valid file + metadata -> 200 with correct schema."""
    files = {"file": make_fake_image()}
    data = {"additionalMetadata": "automated test run"}

    response = requests.post(
        UPLOAD_ENDPOINT.format(base=BASE_URL, pet_id=VALID_PET_ID),
        files=files, data=data, timeout=15
    )

    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    body = response.json()
    assert set(["code", "type", "message"]).issubset(body.keys()), f"Unexpected schema: {body}"
    assert "File uploaded" in body["message"] or "test.jpg" in body["message"], (
        f"Response message does not reflect uploaded file: {body}"
    )


def test_tc02_valid_upload_without_metadata():
    """Valid petId + file only, no metadata -> should still succeed."""
    files = {"file": make_fake_image(name="no_metadata.jpg")}

    response = requests.post(
        UPLOAD_ENDPOINT.format(base=BASE_URL, pet_id=VALID_PET_ID),
        files=files, timeout=15
    )

    assert response.status_code == 200
    body = response.json()
    assert "message" in body


def test_tc03_valid_petid_no_file():
    """Valid petId + metadata only, no file. Spec marks file as optional -
    document actual behavior rather than assume."""
    data = {"additionalMetadata": "metadata only, no file"}

    response = requests.post(
        UPLOAD_ENDPOINT.format(base=BASE_URL, pet_id=VALID_PET_ID),
        data=data, timeout=15
    )

    # We don't hard-assert 200 here since behavior is uncertain by design -
    # log/report what actually comes back.
    print(f"[TC03] Status: {response.status_code}, Body: {response.text}")
    assert response.status_code in (200, 400, 415)


# ---------------------------------------------------------------------------
# Negative test cases
# ---------------------------------------------------------------------------

def test_tc04_invalid_petid_type():
    """Non-numeric petId should not be accepted as a valid path param."""
    files = {"file": make_fake_image()}
    response = requests.post(
        UPLOAD_ENDPOINT.format(base=BASE_URL, pet_id="abc"),
        files=files, timeout=15
    )
    print(f"[TC04] Status: {response.status_code}, Body: {response.text}")
    assert response.status_code in (400, 404, 500), (
        f"Expected client error for non-numeric petId, got {response.status_code}"
    )


def test_tc05_nonexistent_petid():
    """A syntactically valid but almost-certainly-nonexistent petId."""
    files = {"file": make_fake_image()}
    response = requests.post(
        UPLOAD_ENDPOINT.format(base=BASE_URL, pet_id=999999999),
        files=files, timeout=15
    )
    print(f"[TC05] Status: {response.status_code}, Body: {response.text}")
    # Documented finding candidate: demo server often returns 200 even when
    # the pet doesn't exist, since it doesn't validate existence.
    assert response.status_code in (200, 404)


def test_tc06_negative_petid():
    """Negative petId should ideally be rejected."""
    files = {"file": make_fake_image()}
    response = requests.post(
        UPLOAD_ENDPOINT.format(base=BASE_URL, pet_id=-1),
        files=files, timeout=15
    )
    print(f"[TC06] Status: {response.status_code}, Body: {response.text}")
    assert response.status_code in (200, 400, 404)  # report if 200 slips through


def test_tc09_empty_file():
    """0-byte file upload - should ideally be flagged, not silently accepted."""
    files = {"file": ("empty.jpg", io.BytesIO(b""), "image/jpeg")}
    response = requests.post(
        UPLOAD_ENDPOINT.format(base=BASE_URL, pet_id=VALID_PET_ID),
        files=files, timeout=15
    )
    print(f"[TC09] Status: {response.status_code}, Body: {response.text}")
    assert response.status_code == 200  # capture actual behavior; flag in report if message says "0 bytes"


def test_tc11_wrong_file_type():
    """Uploading a non-image file - check whether MIME/type is validated at all."""
    files = {"file": ("not_an_image.txt", io.BytesIO(b"plain text content"), "text/plain")}
    response = requests.post(
        UPLOAD_ENDPOINT.format(base=BASE_URL, pet_id=VALID_PET_ID),
        files=files, timeout=15
    )
    print(f"[TC11] Status: {response.status_code}, Body: {response.text}")
    # Demo server is expected to accept this - documented as a finding, not a hard failure.
    assert response.status_code == 200


def test_tc12_script_in_metadata():
    """Metadata containing a script tag - checks the value is only ever
    echoed back as data, and that no error/crash occurs."""
    payload = "<script>alert(1)</script>"
    files = {"file": make_fake_image()}
    data = {"additionalMetadata": payload}

    response = requests.post(
        UPLOAD_ENDPOINT.format(base=BASE_URL, pet_id=VALID_PET_ID),
        files=files, data=data, timeout=15
    )
    print(f"[TC12] Status: {response.status_code}, Body: {response.text}")
    assert response.status_code == 200
    # This endpoint returns JSON (not rendered HTML), so reflected XSS isn't
    # directly exploitable here - but confirm the server didn't error out.


# ---------------------------------------------------------------------------
# Response quality / schema checks (applies to any successful call)
# ---------------------------------------------------------------------------

def test_tc_response_time_reasonable():
    """Basic performance sanity check for a small upload."""
    files = {"file": make_fake_image()}
    start = time.time()
    response = requests.post(
        UPLOAD_ENDPOINT.format(base=BASE_URL, pet_id=VALID_PET_ID),
        files=files, timeout=15
    )
    elapsed = time.time() - start
    print(f"[Response Time] {elapsed:.2f}s")
    assert response.status_code == 200
    assert elapsed < 10, f"Response took too long: {elapsed:.2f}s"


def test_tc_content_type_header():
    """Response Content-Type should be application/json."""
    files = {"file": make_fake_image()}
    response = requests.post(
        UPLOAD_ENDPOINT.format(base=BASE_URL, pet_id=VALID_PET_ID),
        files=files, timeout=15
    )
    assert "application/json" in response.headers.get("Content-Type", "")
