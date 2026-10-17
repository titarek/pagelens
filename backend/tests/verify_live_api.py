import json
import time
import urllib.request

def test_live_api():
    # 1. Health
    with urllib.request.urlopen("http://127.0.0.1:8000/api/v1/health") as resp:
        health = json.loads(resp.read().decode())
        print("Health status:", health)
        assert health["status"] == "ok"

    # 2. Analyze
    req_data = json.dumps({"url": "https://example.com", "mode": "static"}).encode()
    req = urllib.request.Request(
        "http://127.0.0.1:8000/api/v1/analyze",
        data=req_data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        submit = json.loads(resp.read().decode())
        print("Analyze submitted:", submit)
        job_id = submit["job_id"]
        assert submit["status"] == "queued"

    # 3. Poll report
    report = None
    for i in range(15):
        time.sleep(1)
        with urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/report/{job_id}") as resp:
            data = json.loads(resp.read().decode())
            status = data.get("status")
            print(f"Poll {i+1}: status={status}")
            if status in ("ok", "partial"):
                report = data
                break

    assert report is not None
    print(f"Report retrieved successfully! Overall score: {report['score']['total']}/100")
    print(f"Structural metrics: {report['structural']['html_bytes']} HTML bytes, {report['structural']['num_dom_elements']} DOM elements")
    print(f"Shortcomings count: {len(report['shortcomings'])}")
    print(f"Security checks: {report['security']['passed']} passed, {report['security']['warnings']} warnings, {report['security']['failures']} failures")

    # 4. Export JSON
    with urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/report/{job_id}/export?format=json") as resp:
        json_bytes = resp.read()
        print("Export JSON bytes:", len(json_bytes))
        assert len(json_bytes) > 500

    # 5. Export PDF
    with urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/report/{job_id}/export?format=pdf") as resp:
        pdf_bytes = resp.read()
        print("Export PDF bytes:", len(pdf_bytes))
        assert len(pdf_bytes) > 1000

    # 6. Scraped Source JSON
    with urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/report/{job_id}/source") as resp:
        source_data = json.loads(resp.read().decode())
        print(f"Scraped source JSON retrieved: {source_data['html_bytes']} HTML bytes, {source_data['css_bytes']} CSS bytes")
        assert source_data["html_bytes"] > 0

    # 7. Download Scraped HTML
    with urllib.request.urlopen(f"http://127.0.0.1:8000/api/v1/report/{job_id}/source/download?type=html") as resp:
        raw_html = resp.read()
        print(f"Downloaded raw HTML: {len(raw_html)} bytes")
        assert len(raw_html) > 0

    print("ALL LIVE BACKEND CHECKS PASSED PERFECTLY!")

if __name__ == "__main__":
    test_live_api()
