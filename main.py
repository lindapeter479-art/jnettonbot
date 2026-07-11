import os
import logging
import json
import random
import re
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ContextTypes, 
    filters
)
from utils import DictionaryAPI
from database import Database

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Get environment variables
BOT_TOKEN = os.environ.get("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("No BOT_TOKEN found in environment variables!")

# Initialize utilities
dict_api = DictionaryAPI()
db = Database()

# ============ COMMAND HANDLERS ============

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a welcome message when /start is issued."""
    user = update.effective_user
    
    # Register user in database
    db.add_user(
        user_id=user.id,
        username=user.username or "Unknown",
        first_name=user.first_name or ""
    )
    
    welcome_message = (
        f"🎉 Hello {user.mention_html()}!\n\n"
        "Welcome to **@jnettonbot** - Your Personal Vocabulary Assistant! 📚\n\n"
        "I can help you learn new words, save your favorites, and quiz you on them.\n\n"
        "*📖 Available Commands:*\n"
        "• `/define [word]` - Get definition of a word\n"
        "• `/synonyms [word]` - Find synonyms for a word\n"
        "• `/save [word]` - Save a word to your vocabulary list\n"
        "• `/mylist` - View your saved words\n"
        "• `/quiz` - Take a vocabulary quiz\n"
        "• `/stats` - View your learning statistics\n"
        "• `/help` - Show this help message again\n\n"
        "💡 *Tip:* You can also just type any word to get its definition instantly!\n"
        "🔍 *Tip 2:* Try typing `define [word]` or just the word itself!"
    )
    await update.message.reply_html(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send a help message when /help is issued."""
    help_text = (
        "*📚 @jnettonbot - Help Center*\n\n"
        "*Commands:*\n"
        "/start - Start the bot\n"
        "/define [word] - Get definition of a word\n"
        "/synonyms [word] - Find synonyms for a word\n"
        "/save [word] - Save a word to your vocabulary list\n"
        "/mylist - View your saved words\n"
        "/quiz - Take a vocabulary quiz\n"
        "/stats - View your learning statistics\n"
        "/help - Show this message\n\n"
        "*Examples:*\n"
        "• `/define serendipity`\n"
        "• `/define dental care` (multi-word)\n"
        "• `/save eloquent`\n"
        "• Just type a word like `benevolent`\n\n"
        "*Need more help?*\n"
        "Contact @your_support_username"
    )
    await update.message.reply_markdown(help_text)

async def define_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get definition of a word or phrase."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a word or phrase.\n"
            "Example: `/define serendipity`\n"
            "Example: `/define dental care`"
        )
        return
    
    # Join all args to handle multi-word phrases
    word_phrase = " ".join(context.args).strip().lower()
    
    # If it's a single word, look it up directly
    # If it's a phrase, try to find the main word (last word or most significant word)
    words = word_phrase.split()
    
    # Try to find the most relevant word (usually the last word or a noun)
    # For "meaning of dental", we want "dental"
    # For "define dental", we want "dental"
    
    # Remove common stop words and find the main word
    stop_words = {'meaning', 'of', 'define', 'what', 'is', 'the', 'a', 'an', 'for'}
    main_words = [w for w in words if w not in stop_words]
    
    if main_words:
        # Use the first meaningful word, or the last one
        search_word = main_words[-1] if len(main_words) > 1 else main_words[0]
    else:
        search_word = words[-1]  # Fallback to last word
    
    await update.message.reply_text(f"🔍 Looking up definition for *{search_word}*...", parse_mode='Markdown')
    
    result = dict_api.get_definition(search_word)
    
    if result.get("error"):
        await update.message.reply_text(
            f"❌ Sorry, I couldn't find the definition for '{search_word}'.\n"
            "Please check the spelling or try another word."
        )
        return
    
    # Format the response
    response = f"*📖 {search_word.capitalize()}*\n"
    if len(words) > 1:
        response += f"*Query:* \"{word_phrase}\"\n\n"
    response += "\n"
    
    for meaning in result.get("meanings", [])[:2]:
        part_of_speech = meaning.get("partOfSpeech", "").capitalize()
        response += f"*{part_of_speech}*\n"
        
        for i, definition in enumerate(meaning.get("definitions", [])[:2], 1):
            response += f"{i}. {definition.get('definition', '')}\n"
            if definition.get("example"):
                response += f"   _Example: {definition.get('example')}_\n"
        
        if meaning.get("synonyms"):
            synonyms = ", ".join(meaning.get("synonyms")[:5])
            response += f"*Synonyms:* {synonyms}\n"
        
        response += "\n"
    
    # Add option to save the word
    keyboard = [
        [InlineKeyboardButton("💾 Save Word", callback_data=f"save_{search_word}")],
        [InlineKeyboardButton("🔄 Get More Examples", callback_data=f"examples_{search_word}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_markdown(response, reply_markup=reply_markup)
    
    # Log the lookup
    db.add_word_search(user_id=update.effective_user.id, word=search_word)

async def get_synonyms(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Find synonyms for a word or phrase."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a word.\n"
            "Example: `/synonyms happy`"
        )
        return
    
    # Join all args to handle multi-word phrases
    word_phrase = " ".join(context.args).strip().lower()
    words = word_phrase.split()
    
    # Extract the main word
    stop_words = {'meaning', 'of', 'define', 'what', 'is', 'the', 'a', 'an', 'for', 'synonyms', 'synonym'}
    main_words = [w for w in words if w not in stop_words]
    search_word = main_words[-1] if main_words else words[-1]
    
    result = dict_api.get_synonyms(search_word)
    
    if result.get("error"):
        await update.message.reply_text(
            f"❌ Sorry, I couldn't find synonyms for '{search_word}'. Please try another word."
        )
        return
    
    synonyms = result.get("synonyms", [])
    if not synonyms:
        await update.message.reply_text(f"ℹ️ No synonyms found for '{search_word}'.")
        return
    
    response = f"*🔄 Synonyms for '{search_word.capitalize()}':*\n\n"
    response += "• " + "\n• ".join(synonyms[:15])
    
    await update.message.reply_markdown(response)

async def save_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Save a word to user's vocabulary list."""
    if not context.args:
        await update.message.reply_text(
            "❌ Please provide a word to save.\n"
            "Example: `/save serendipity`"
        )
        return
    
    # Join all args to handle multi-word phrases
    word_phrase = " ".join(context.args).strip().lower()
    words = word_phrase.split()
    
    # Extract the main word
    stop_words = {'meaning', 'of', 'define', 'what', 'is', 'the', 'a', 'an', 'for', 'save'}
    main_words = [w for w in words if w not in stop_words]
    search_word = main_words[-1] if main_words else words[-1]
    
    user_id = update.effective_user.id
    
    # Get definition first to store with the word
    result = dict_api.get_definition(search_word)
    definition = result.get("meanings", [{}])[0].get("definitions", [{}])[0].get("definition", "")
    part_of_speech = result.get("meanings", [{}])[0].get("partOfSpeech", "")
    
    if definition:
        if db.save_word(user_id, search_word, definition, part_of_speech):
            await update.message.reply_text(
                f"✅ *{search_word.capitalize()}* has been saved to your vocabulary list!\n"
                f"📚 You now have {db.get_saved_words_count(user_id)} words saved.",
                parse_mode='Markdown'
            )
        else:
            await update.message.reply_text(
                f"ℹ️ *{search_word.capitalize()}* is already in your saved words!",
                parse_mode='Markdown'
            )
    else:
        await update.message.reply_text(
            f"❌ Could not find definition for '{search_word}'. Please check the spelling."
        )

async def my_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Display user's saved words."""
    user_id = update.effective_user.id
    words = db.get_saved_words(user_id)
    
    if not words:
        await update.message.reply_text(
            "📭 You haven't saved any words yet.\n"
            "Use `/save [word]` to build your vocabulary list!"
        )
        return
    
    response = f"*📚 Your Saved Words ({len(words)} total)*\n\n"
    
    # Show words in groups of 10 with pagination
    page = 0
    if context.args and context.args[0].isdigit():
        page = int(context.args[0]) - 1
    
    start_idx = page * 10
    end_idx = min(start_idx + 10, len(words))
    
    for i, word_data in enumerate(words[start_idx:end_idx], start=start_idx + 1):
        word = word_data.get('word', '').capitalize()
        definition = word_data.get('definition', 'No definition')
        if len(definition) > 40:
            definition = definition[:40] + "..."
        response += f"{i}. *{word}* - {definition}\n"
    
    # Add pagination
    total_pages = (len(words) + 9) // 10
    if total_pages > 1:
        response += f"\n📄 Page {page + 1} of {total_pages}"
        keyboard = []
        if page > 0:
            keyboard.append(InlineKeyboardButton("⬅️ Previous", callback_data=f"page_{page}"))
        if page < total_pages - 1:
            keyboard.append(InlineKeyboardButton("Next ➡️", callback_data=f"page_{page + 2}"))
        
        if keyboard:
            reply_markup = InlineKeyboardMarkup([keyboard])
            await update.message.reply_markdown(response, reply_markup=reply_markup)
        else:
            await update.message.reply_markdown(response)
    else:
        await update.message.reply_markdown(response)

async def take_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start a vocabulary quiz."""
    user_id = update.effective_user.id
    
    # Get random words from user's saved list or common words
    saved_words = db.get_saved_words(user_id)
    
    if saved_words and len(saved_words) >= 4:
        # Use saved words
        words = random.sample(saved_words, min(4, len(saved_words)))
    else:
        # Use common words from the API
        common_words = ["serendipity", "eloquent", "benevolent", "ephemeral", "ubiquitous", 
                       "meticulous", "profound", "resilient", "innovative", "compassionate"]
        words = [{"word": w} for w in random.sample(common_words, 4)]
    
    # Get definitions for each word
    quiz_data = []
    for word_data in words:
        word = word_data.get('word', '')
        result = dict_api.get_definition(word)
        if not result.get("error"):
            definition = result.get("meanings", [{}])[0].get("definitions", [{}])[0].get("definition", "")
            quiz_data.append({"word": word, "definition": definition})
    
    if len(quiz_data) < 2:
        await update.message.reply_text(
            "❌ Not enough words available for a quiz.\n"
            "Try saving more words first with `/save [word]`!"
        )
        return
    
    # Pick a random word for the quiz
    correct_word = random.choice(quiz_data)
    word_to_guess = correct_word["word"]
    correct_definition = correct_word["definition"]
    
    # Get distractors
    distractors = [d["definition"] for d in quiz_data if d["word"] != word_to_guess]
    while len(distractors) < 3:
        distractors.append("A word that means something completely different")
    
    # Build options (1 correct + 3 distractors)
    options = [correct_definition] + random.sample(distractors, min(3, len(distractors)))
    random.shuffle(options)
    
    # Store correct answer in context
    context.user_data['quiz_answer'] = correct_definition
    context.user_data['quiz_word'] = word_to_guess
    
    # Create buttons for options
    keyboard = []
    for i, option in enumerate(options):
        # Truncate long definitions for button text
        button_text = option[:40] + "..." if len(option) > 40 else option
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"quiz_{i}")])
    
    # Store options for validation
    context.user_data['quiz_options'] = options
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        f"🧠 *Vocabulary Quiz*\n\n"
        f"Which word matches this definition?\n\n"
        f"*Definition:* _{correct_definition}_\n\n"
        f"Choose the correct word:",
        parse_mode='Markdown',
        reply_markup=reply_markup
    )

async def show_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show user's learning statistics."""
    user_id = update.effective_user.id
    stats = db.get_user_stats(user_id)
    
    if not stats:
        await update.message.reply_text(
            "📊 You haven't started learning yet!\n"
            "Start by looking up words or saving your favorites."
        )
        return
    
    response = (
        f"*📊 Your Learning Statistics*\n\n"
        f"📚 Words saved: {stats.get('saved_words', 0)}\n"
        f"🔍 Words looked up: {stats.get('total_searches', 0)}\n"
        f"🎯 Quiz attempts: {stats.get('quiz_attempts', 0)}\n"
        f"✅ Quiz correct: {stats.get('quiz_correct', 0)}\n"
        f"📈 Success rate: {stats.get('success_rate', 0)}%\n"
        f"🏆 Total points: {stats.get('points', 0)}\n\n"
        f"Keep learning and building your vocabulary! 💪"
    )
    await update.message.reply_markdown(response)

# ============ MESSAGE HANDLER ============

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages (for instant word lookup)."""
    text = update.message.text.strip()
    
    # Ignore if it's a command
    if text.startswith('/'):
        return
    
    # Check if it's too short
    if len(text) < 2:
        return
    
    # Check if user is asking "meaning of X" or "define X"
    # Extract the word from natural language queries
    text_lower = text.lower()
    search_word = None
    
    # Pattern: "meaning of [word]"
    if "meaning of" in text_lower:
        # Extract after "meaning of"
        parts = text_lower.split("meaning of", 1)
        if len(parts) > 1:
            words = parts[1].strip().split()
            if words:
                # Remove stop words and get the last meaningful word
                stop_words = {'the', 'a', 'an', 'for', 'to', 'of'}
                main_words = [w for w in words if w not in stop_words]
                search_word = main_words[-1] if main_words else words[-1]
    
    # Pattern: "define [word]"
    elif "define" in text_lower:
        parts = text_lower.split("define", 1)
        if len(parts) > 1:
            words = parts[1].strip().split()
            if words:
                stop_words = {'the', 'a', 'an', 'for', 'to', 'of'}
                main_words = [w for w in words if w not in stop_words]
                search_word = main_words[-1] if main_words else words[-1]
    
    # Pattern: "what is [word]"
    elif "what is" in text_lower:
        parts = text_lower.split("what is", 1)
        if len(parts) > 1:
            words = parts[1].strip().split()
            if words:
                stop_words = {'the', 'a', 'an', 'for', 'to', 'of'}
                main_words = [w for w in words if w not in stop_words]
                search_word = main_words[-1] if main_words else words[-1]
    
    # If no pattern matched, use the entire text as a single word (if it's alphabetic)
    else:
        # Remove punctuation and check if it's a single word
        clean_text = re.sub(r'[^\w\s]', '', text).strip()
        if clean_text and len(clean_text.split()) == 1:
            search_word = clean_text.lower()
        else:
            # Try to extract the last word or most significant word
            words = clean_text.split()
            if words:
                search_word = words[-1].lower()
    
    # If we couldn't find a word, try to use the last word in the text
    if not search_word:
        words = text.split()
        if words:
            search_word = words[-1].lower()
        else:
            await update.message.reply_text(
                "ℹ️ I couldn't understand which word to look up.\n"
                "Try: `/define [word]` or just type a single word."
            )
            return
    
    # Validate the word (letters only, allow apostrophes)
    if not re.match(r"^[a-zA-Z']+$", search_word):
        await update.message.reply_text(
            f"ℹ️ Please send a valid word (letters only).\n"
            f"I understood: '{search_word}'"
        )
        return
    
    # Look up the word
    result = dict_api.get_definition(search_word)
    
    if result.get("error"):
        await update.message.reply_text(
            f"❌ I don't know the word '{search_word}'. Please check the spelling."
        )
        return
    
    # Format the response
    response = f"*📖 {search_word.capitalize()}*\n"
    if text_lower != search_word:
        response += f"*Query:* \"{text}\"\n\n"
    response += "\n"
    
    for meaning in result.get("meanings", [])[:2]:
        part_of_speech = meaning.get("partOfSpeech", "").capitalize()
        response += f"*{part_of_speech}*\n"
        
        for i, definition in enumerate(meaning.get("definitions", [])[:2], 1):
            response += f"{i}. {definition.get('definition', '')}\n"
            if definition.get("example"):
                response += f"   _Example: {definition.get('example')}_\n"
        
        if meaning.get("synonyms"):
            synonyms = ", ".join(meaning.get("synonyms")[:5])
            response += f"*Synonyms:* {synonyms}\n"
        
        response += "\n"
    
    # Add action buttons
    keyboard = [
        [InlineKeyboardButton("💾 Save This Word", callback_data=f"save_{search_word}")],
        [InlineKeyboardButton("🔄 Synonyms", callback_data=f"synonyms_{search_word}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_markdown(response, reply_markup=reply_markup)
    
    # Log the lookup
    db.add_word_search(user_id=update.effective_user.id, word=search_word)

# ============ CALLBACK QUERY HANDLER ============

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button presses."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    
    if data.startswith("save_"):
        word = data.replace("save_", "")
        result = dict_api.get_definition(word)
        definition = result.get("meanings", [{}])[0].get("definitions", [{}])[0].get("definition", "")
        part_of_speech = result.get("meanings", [{}])[0].get("partOfSpeech", "")
        
        if db.save_word(user_id, word, definition, part_of_speech):
            await query.edit_message_text(
                f"✅ *{word.capitalize()}* has been saved to your vocabulary list!",
                parse_mode='Markdown'
            )
        else:
            await query.edit_message_text(
                f"ℹ️ *{word.capitalize()}* is already in your saved words!",
                parse_mode='Markdown'
            )
    
    elif data.startswith("synonyms_"):
        word = data.replace("synonyms_", "")
        result = dict_api.get_synonyms(word)
        synonyms = result.get("synonyms", [])[:10]
        
        if synonyms:
            response = f"*🔄 Synonyms for '{word.capitalize()}':*\n\n"
            response += "• " + "\n• ".join(synonyms)
            await query.edit_message_text(response, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"ℹ️ No synonyms found for '{word}'.")
    
    elif data.startswith("examples_"):
        word = data.replace("examples_", "")
        result = dict_api.get_definition(word)
        
        examples = []
        for meaning in result.get("meanings", []):
            for definition in meaning.get("definitions", []):
                if definition.get("example"):
                    examples.append(definition.get("example"))
        
        if examples:
            response = f"*📝 Examples for '{word.capitalize()}':*\n\n"
            for i, example in enumerate(examples[:5], 1):
                response += f"{i}. {example}\n"
            await query.edit_message_text(response, parse_mode='Markdown')
        else:
            await query.edit_message_text(f"ℹ️ No examples found for '{word}'.")
    
    elif data.startswith("quiz_"):
        # Handle quiz answer
        selected_idx = int(data.replace("quiz_", ""))
        options = context.user_data.get('quiz_options', [])
        correct_answer = context.user_data.get('quiz_answer', '')
        word = context.user_data.get('quiz_word', '')
        
        if selected_idx < len(options):
            selected = options[selected_idx]
            is_correct = selected == correct_answer
            
            if is_correct:
                db.update_quiz_result(user_id, True)
                response = f"✅ *Correct!* 🎉\n\nThe word is *{word.capitalize()}*\n\nKeep up the great work!"
            else:
                db.update_quiz_result(user_id, False)
                response = f"❌ Not quite right.\n\n"
                response += f"The correct word was *{word.capitalize()}*\n"
                response += f"Definition: _{correct_answer}_\n\n"
                response += "Keep learning! 💪"
            
            await query.edit_message_text(response, parse_mode='Markdown')
    
    elif data.startswith("page_"):
        # Handle pagination
        page = int(data.replace("page_", ""))
        context.args = [str(page)]
        await my_list(update, context)

# ============ MAIN FUNCTION ============

def main():
    """Start the bot using Long Polling."""
    # Create the Application
    application = ApplicationBuilder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("define", define_word))
    application.add_handler(CommandHandler("synonyms", get_synonyms))
    application.add_handler(CommandHandler("save", save_word))
    application.add_handler(CommandHandler("mylist", my_list))
    application.add_handler(CommandHandler("quiz", take_quiz))
    application.add_handler(CommandHandler("stats", show_stats))
    
    # Register message and callback handlers
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Start the bot
    logger.info("🚀 Starting @jnettonbot with long polling...")
    application.run_polling()

if __name__ == "__main__":
    main()
