# @jnettonbot - Your Personal Vocabulary Assistant

A Telegram bot for learning new words, building vocabulary, and quizzing yourself.

## Features

- 📖 **Word Definitions**: Look up definitions instantly
- 🔄 **Synonyms**: Find synonyms for any word
- 💾 **Save Words**: Build your personal vocabulary list
- 📚 **My List**: View all your saved words
- 🧠 **Quiz**: Test your vocabulary knowledge
- 📊 **Statistics**: Track your learning progress

## Deployment

### On Railway

1. Fork this repository
2. Create a new project on Railway
3. Connect your GitHub repository
4. Add `BOT_TOKEN` as an environment variable
5. Deploy!

### Local Development

1. Clone the repository
2. Create a virtual environment
3. Install dependencies: `pip install -r requirements.txt`
4. Set up `.env` file with your bot token
5. Run: `python main.py`

## Commands

- `/start` - Start the bot
- `/define [word]` - Get definition
- `/synonyms [word]` - Get synonyms
- `/save [word]` - Save a word
- `/mylist` - View saved words
- `/quiz` - Take a quiz
- `/stats` - View statistics
- `/help` - Show help

## Technologies

- Python 3.9+
- python-telegram-bot
- Dictionary API
- SQLite
- Railway

## License

MIT
