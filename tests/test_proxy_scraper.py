import json
from pathlib import Path


class FakeResponse:
    def __init__(self, body: str):
        self._body = body.encode("utf-8")

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def load_module():
    import proxy_scraper

    return proxy_scraper


def test_fetch_proxyscrape_parses_line_list(monkeypatch):
    proxy_scraper = load_module()

    body = """1.1.1.1:80

 2.2.2.2:8080 
not-a-proxy
1.1.1.1:80
"""

    def fake_urlopen(request, timeout=None):
        return FakeResponse(body)

    monkeypatch.setattr(proxy_scraper.urllib.request, "urlopen", fake_urlopen)

    assert proxy_scraper.fetch_proxyscrape() == [
        "1.1.1.1:80",
        "2.2.2.2:8080",
        "1.1.1.1:80",
    ]


def test_fetch_free_proxy_list_parses_html_table(monkeypatch):
    proxy_scraper = load_module()

    html = """
    <html>
      <body>
        <table id="proxylisttable">
          <thead>
            <tr><th>IP Address</th><th>Port</th><th>Country</th></tr>
          </thead>
          <tbody>
            <tr><td>3.3.3.3</td><td>3128</td><td>US</td></tr>
            <tr><td>4.4.4.4</td><td>8080</td><td>DE</td></tr>
          </tbody>
        </table>
      </body>
    </html>
    """

    def fake_urlopen(request, timeout=None):
        return FakeResponse(html)

    monkeypatch.setattr(proxy_scraper.urllib.request, "urlopen", fake_urlopen)

    assert proxy_scraper.fetch_free_proxy_list() == [
        "3.3.3.3:3128",
        "4.4.4.4:8080",
    ]


def test_fetch_geonode_parses_json_api(monkeypatch):
    proxy_scraper = load_module()

    payload = {
        "data": [
            {"ip": "5.5.5.5", "port": 8000},
            {"ip": "6.6.6.6", "port": "8080"},
            {"ip": "", "port": 9000},
        ]
    }

    def fake_urlopen(request, timeout=None):
        return FakeResponse(json.dumps(payload))

    monkeypatch.setattr(proxy_scraper.urllib.request, "urlopen", fake_urlopen)

    assert proxy_scraper.fetch_geonode() == [
        "5.5.5.5:8000",
        "6.6.6.6:8080",
    ]


def test_deduplicate_preserves_order_and_normalizes():
    proxy_scraper = load_module()

    assert proxy_scraper.deduplicate([
        "1.1.1.1:80",
        " 1.1.1.1:80 ",
        "",
        "2.2.2.2:8080",
        "2.2.2.2:8080",
        "http://3.3.3.3:3128",
    ]) == [
        "1.1.1.1:80",
        "2.2.2.2:8080",
        "3.3.3.3:3128",
    ]


def test_save_proxies_appends_unique_lines(tmp_path):
    proxy_scraper = load_module()

    output = tmp_path / "proxies" / "proxyscrape_raw.txt"
    output.parent.mkdir()
    output.write_text("1.1.1.1:80\n")

    written = proxy_scraper.save_proxies(
        ["1.1.1.1:80", "2.2.2.2:8080", "2.2.2.2:8080"],
        str(output),
    )

    assert written == 1
    assert output.read_text().splitlines() == ["1.1.1.1:80", "2.2.2.2:8080"]


def test_scrape_all_fetches_all_sources_and_saves(tmp_path, monkeypatch):
    proxy_scraper = load_module()

    calls = []

    monkeypatch.setattr(proxy_scraper, "DEFAULT_OUTPUT_PATH", str(tmp_path / "proxyscrape_raw.txt"))
    monkeypatch.setattr(proxy_scraper, "fetch_proxyscrape", lambda: calls.append("proxyscrape") or ["1.1.1.1:80", "2.2.2.2:8080"])
    monkeypatch.setattr(proxy_scraper, "fetch_free_proxy_list", lambda: calls.append("free") or ["2.2.2.2:8080", "3.3.3.3:3128"])
    monkeypatch.setattr(proxy_scraper, "fetch_geonode", lambda: calls.append("geonode") or ["3.3.3.3:3128", "4.4.4.4:9000"])

    result = proxy_scraper.scrape_all()

    assert calls == ["proxyscrape", "free", "geonode"]
    assert result["total"] == 4
    assert result["sources"] == {
        "proxyscrape": ["1.1.1.1:80", "2.2.2.2:8080"],
        "free_proxy_list": ["2.2.2.2:8080", "3.3.3.3:3128"],
        "geonode": ["3.3.3.3:3128", "4.4.4.4:9000"],
    }
    assert result["proxies"] == [
        "1.1.1.1:80",
        "2.2.2.2:8080",
        "3.3.3.3:3128",
        "4.4.4.4:9000",
    ]
    assert Path(tmp_path / "proxyscrape_raw.txt").read_text().splitlines() == [
        "1.1.1.1:80",
        "2.2.2.2:8080",
        "3.3.3.3:3128",
        "4.4.4.4:9000",
    ]


def test_main_with_source_argument_fetches_only_requested_source(tmp_path, monkeypatch):
    proxy_scraper = load_module()

    called = []

    monkeypatch.setattr(proxy_scraper, "fetch_proxyscrape", lambda: called.append("proxyscrape") or ["1.1.1.1:80"])
    monkeypatch.setattr(proxy_scraper, "fetch_free_proxy_list", lambda: called.append("free") or ["2.2.2.2:8080"])
    monkeypatch.setattr(proxy_scraper, "fetch_geonode", lambda: called.append("geonode") or ["3.3.3.3:3128"])

    captured = {}

    def fake_save_proxies(proxies, path):
        captured["proxies"] = list(proxies)
        captured["path"] = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        Path(path).write_text("\n".join(proxies) + ("\n" if proxies else ""))
        return len(proxies)

    monkeypatch.setattr(proxy_scraper, "save_proxies", fake_save_proxies)

    output = tmp_path / "custom" / "out.txt"
    result = proxy_scraper.main(["--source", "2", "--output", str(output)])

    assert called == ["free"]
    assert captured["proxies"] == ["2.2.2.2:8080"]
    assert captured["path"] == str(output)
    assert result["proxies"] == ["2.2.2.2:8080"]
