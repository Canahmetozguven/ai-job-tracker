import pytest

from scripts.check_secrets import find_secrets


def test_secret_scan_detects_telegram_bot_token():
    token = "123456789:" + "A" * 35

    assert "Telegram bot token" in find_secrets(token)


def test_secret_scan_allows_documented_placeholders():
    assert find_secrets("TELEGRAM_BOT_TOKEN=your-bot-token-here") == []


@pytest.mark.parametrize(
    "variable_name",
    ["OPENAI_API_KEY", "AWS_SECRET_ACCESS_KEY", "SERVICE_PASSWORD"],
)
def test_secret_scan_detects_prefixed_credential_names(variable_name):
    assignment = f"{variable_name}=sk-" + "A" * 32

    assert "credential assignment" in find_secrets(assignment)


def test_secret_scan_detects_encrypted_pkcs8_private_key():
    header = "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----"

    assert "private key" in find_secrets(header)


def test_secret_scan_detects_quoted_json_credential_key():
    assignment = '"OPENAI_API_KEY": "sk-proj-' + "A" * 32 + '"'

    assert "credential assignment" in find_secrets(assignment)


def test_secret_scan_detects_password_with_punctuation():
    password = "P@ssw0rd-with" + "-many-chars-123"
    assignment = f'SERVICE_PASSWORD="{password}"'

    assert "credential assignment" in find_secrets(assignment)
