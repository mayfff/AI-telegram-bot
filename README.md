# 🤖 Telegram Bot — Gemini Menu Assistant

A simple Telegram bot with a keyboard-based menu and Google Gemini integration.  
It allows users to send prompts to Gemini and receive AI-generated responses directly in Telegram.

---

## 🛠 Technologies Used

- Python 3.10+
- python-telegram-bot 22.5
- google-genai 1.50.1
- python-dotenv

---

## 📦 Getting Started

### 1. Clone the repository

```bash
git clone <YOUR_REPO_URL>
cd <PROJECT_FOLDER>
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

If you don’t have `requirements.txt`:

```bash
pip install python-telegram-bot==22.5 google-genai==1.50.1 python-dotenv
```

---

## 🔐 Environment Variables

Create a `.env` file in the project root:

```env
TELEGRAM_TOKEN=YOUR_TELEGRAM_BOT_TOKEN
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
GEMINI_MODEL=gemini-2.5-flash
```

- `TELEGRAM_TOKEN` — token from @BotFather  
- `GEMINI_API_KEY` — your Gemini API key (Google AI Studio)  
- `GEMINI_MODEL` — optional (default: gemini-2.5-flash)  

---

## 3. ▶ Run the Bot

```bash
python bot.py
```
