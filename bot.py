import os
import requests
from telegram import Update, ChatAction, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, ContextTypes,
    MessageHandler, CallbackQueryHandler, filters
)

import os
BOT_TOKEN = os.environ.get("BOT_TOKEN")
LOG_CHANNEL = '@JS_91Club_Prediction'
ADMIN_IDS = [1445606646]

user_history = {}
last_prompts = {}  # Store prompt per user for regenerate

# --- Commands ---

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 Welcome! Use `/gen <prompt>` to generate an AI image.")

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("ℹ️ *Bot Commands:*\n"
                                    "`/gen <prompt>` - Generate AI image\n"
                                    "`/menu` - Show action buttons\n"
                                    "`/info` - View your prompt history\n"
                                    "`/stop` - (Admin only)",
                                    parse_mode="Markdown")

async def info_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    prompts = user_history.get(uid, [])
    if not prompts:
        await update.message.reply_text("🕵️ No prompt history found.")
    else:
        history = "\n".join(f"{i+1}. {p}" for i, p in enumerate(prompts[-10:]))
        await update.message.reply_text(f"📜 Your Last Prompts:\n{history}")

async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id in ADMIN_IDS:
        await update.message.reply_text("🔒 Bot is shutting down.")
        raise SystemExit
    else:
        await update.message.reply_text("❌ You are not authorized.")

# --- Generation Logic ---

async def generate_prompt(update, context, prompt):
    prompt_encoded = prompt.replace(" ", "+")
    image_url = f"https://image.pollinations.ai/prompt/{prompt_encoded}"

    uid = update.effective_user.id
    user_history.setdefault(uid, []).append(prompt)
    last_prompts[uid] = prompt  # Save for regenerate

    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=ChatAction.UPLOAD_PHOTO)
    msg = await update.message.reply_text("⏳ Generating your image... This may take up to 3 minutes...")

    def fetch_image():
        try:
            res = requests.get(image_url, timeout=180)
            if res.status_code == 200 and 'image' in res.headers.get('Content-Type', ''):
                return True, image_url
        except:
            pass
        return False, None

    success, image = fetch_image()
    if not success:
        await msg.edit_text("♻️ First attempt failed. Retrying...")
        success, image = fetch_image()

    if success:
        caption = f"✅ Prompt: `{prompt}`"
        await context.bot.send_photo(chat_id=update.effective_chat.id, photo=image, caption=caption, parse_mode="Markdown")
        await msg.delete()
        try:
            await context.bot.send_photo(chat_id=LOG_CHANNEL, photo=image,
                                         caption=f"📝 *Prompt from {update.effective_user.first_name}*:\n`{prompt}`",
                                         parse_mode="Markdown")
        except Exception as e:
            print(f"[Log Error] {e}")
    else:
        await msg.edit_text("❌ Image generation failed after retrying. Try again later.")

# --- /gen command ---

async def generate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Please provide a prompt.\nUsage: `/gen cute cat`", parse_mode="Markdown")
        return
    prompt = " ".join(context.args)
    await generate_prompt(update, context, prompt)

# --- Auto-reply Handler ---

async def auto_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.lower()
    if "hello" in text or "hi" in text:
        await update.message.reply_text("👋 Hello! Use /gen to generate an image.")
    elif "bye" in text:
        await update.message.reply_text("👋 Goodbye!")
    elif "menu" in text:
        await show_buttons(update, context)

# --- Inline Button Command ---

async def show_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    buttons = [
        [InlineKeyboardButton("🔁 Regenerate", callback_data="regenerate")],
        [InlineKeyboardButton("ℹ️ Help", callback_data="help")]
    ]
    markup = InlineKeyboardMarkup(buttons)
    await update.message.reply_text("👇 Choose an option:", reply_markup=markup)

# --- Handle Inline Button Clicks ---

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id

    if query.data == "regenerate":
        prompt = last_prompts.get(uid)
        if prompt:
            fake_update = Update(update.update_id, message=query.message)
            await generate_prompt(fake_update, context, prompt)
        else:
            await query.edit_message_text("❌ No previous prompt to regenerate.")
    elif query.data == "help":
        await query.edit_message_text("Use /gen <prompt> to generate AI images.\nTry /menu for buttons.")

# --- Unknown command handler ---

async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "❌ Unknown or unsupported command.\n✅ Use `/gen <prompt>` or `/help` to see available commands.",
        parse_mode="Markdown"
    )

# --- Main ---

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("info", info_cmd))
    app.add_handler(CommandHandler("gen", generate))
    app.add_handler(CommandHandler("stop", shutdown))
    app.add_handler(CommandHandler("menu", show_buttons))

    app.add_handler(CallbackQueryHandler(button_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, auto_reply))
    app.add_handler(MessageHandler(filters.COMMAND, unknown_command))  # Must be last

    print("🤖 Bot is running...")
    app.run_polling()
