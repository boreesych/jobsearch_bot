# JobSearch Bot 🤖

A Telegram bot that periodically checks for new Python job postings using the [Adzuna API](https://developer.adzuna.com/) and sends them to a Telegram chat.

## Features

- Fetches recent job listings from Adzuna.
- Parses and formats job data including title, company, location, and link.
- Sends job postings directly to a specified Telegram chat.
- Includes robust error handling and logging.

## Requirements

- Python 3.7+
- A [Telegram bot token](https://core.telegram.org/bots#3-how-do-i-create-a-bot)
- A Telegram chat ID
- [Adzuna API credentials](https://developer.adzuna.com/)

## Set up environment variables:

Create a .env file in the project root:

```
TELEGRAM_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
API_KEY=your_adzuna_api_key
API_ID=your_adzuna_app_id
```

## Configuration

You can customize the following in jobsearch_bot.py:
- COUNTRY – change to your preferred country code (e.g., us, gb, de, etc.)
- PARAMS['what'] – change the search query (e.g., 'python', 'data scientist')
- RETRY_PERIOD – change the polling interval (default is 600 seconds)

## Logging

Logs are printed to stdout and include detailed info about requests, responses, and any errors encountered.

## License

This project is licensed under the MIT License.