from scripts.check_secrets import find_secrets


def test_secret_scan_detects_telegram_bot_token():
    token = "123456789:" + "A" * 35

    assert "Telegram bot token" in find_secrets(token)


def test_secret_scan_allows_documented_placeholders():
    assert find_secrets("TELEGRAM_BOT_TOKEN=your-bot-token-here") == []
