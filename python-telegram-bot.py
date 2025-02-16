import os
import logging
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Google Cloud client libraries
from google.cloud import speech
from google.cloud import vision

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment Variables (set these in your system or a .env file)
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN")
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")  # if your AI endpoint requires it

# Replace with your actual AI endpoint (this is a placeholder)
GOOGLE_AI_ENDPOINT = "https://your-google-ai-studio-endpoint/api/gemini"

def start(update: Update, context: CallbackContext):
    update.message.reply_text("Hello! I am Gemini – your multi-input AI assistant.")

def process_text_with_ai(input_text: str) -> str:
    """
    Sends the input text to the Google AI endpoint and returns the response.
    Adjust the payload/headers based on the API’s requirements.
    """
    payload = {
        "input": input_text,
        "api_key": GOOGLE_API_KEY  # if needed
    }
    try:
        response = requests.post(GOOGLE_AI_ENDPOINT, json=payload, timeout=10)
        response.raise_for_status()
        data = response.json()
        return data.get("response", "I did not understand that.")
    except Exception as e:
        logger.error(f"Error calling AI endpoint: {e}")
        return "Sorry, there was an error processing your request."

def handle_text(update: Update, context: CallbackContext):
    user_text = update.message.text
    logger.info(f"Received text: {user_text}")
    ai_response = process_text_with_ai(user_text)
    update.message.reply_text(ai_response)

def handle_voice(update: Update, context: CallbackContext):
    voice = update.message.voice
    file = voice.get_file()
    logger.info("Downloading voice message...")
    audio_bytes = file.download_as_bytearray()

    # Initialize Speech client (ensure GOOGLE_APPLICATION_CREDENTIALS is set)
    speech_client = speech.SpeechClient()
    audio = speech.RecognitionAudio(content=audio_bytes)
    config = speech.RecognitionConfig(
        # Adjust encoding based on Telegram’s voice file format (typically OGG_OPUS)
        encoding=speech.RecognitionConfig.AudioEncoding.OGG_OPUS,
        language_code="en-US"
    )

    try:
        response = speech_client.recognize(config=config, audio=audio)
        transcript = " ".join(result.alternatives[0].transcript for result in response.results)
        logger.info(f"Transcription: {transcript}")
        if transcript:
            ai_response = process_text_with_ai(transcript)
            update.message.reply_text(ai_response)
        else:
            update.message.reply_text("Sorry, I couldn't transcribe your voice message.")
    except Exception as e:
        logger.error(f"Speech-to-Text error: {e}")
        update.message.reply_text("Error processing your voice message.")

def handle_image(update: Update, context: CallbackContext):
    # Get the highest resolution photo
    photo = update.message.photo[-1]
    file = photo.get_file()
    logger.info("Downloading image...")
    image_bytes = file.download_as_bytearray()

    # Initialize Vision client
    vision_client = vision.ImageAnnotatorClient()
    image = vision.Image(content=image_bytes)
    
    try:
        response = vision_client.label_detection(image=image)
        labels = response.label_annotations
        if labels:
            description = "I see: " + ", ".join(label.description for label in labels)
            logger.info(f"Image labels: {description}")
            # Optionally, pass this description to your AI endpoint for further processing
            ai_response = process_text_with_ai(description)
            update.message.reply_text(ai_response)
        else:
            update.message.reply_text("I couldn't determine what was in the image.")
    except Exception as e:
        logger.error(f"Vision API error: {e}")
        update.message.reply_text("Error processing the image.")

def main():
    # Create the Updater and pass it your bot's token.
    updater = Updater(TELEGRAM_TOKEN)
    dispatcher = updater.dispatcher

    # Handlers for commands and messages
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    dispatcher.add_handler(MessageHandler(Filters.voice, handle_voice))
    dispatcher.add_handler(MessageHandler(Filters.photo, handle_image))

    # Start the Bot (using polling; for production, consider setting up a webhook)
    updater.start_polling()
    logger.info("Bot is up and running...")
    updater.idle()

if __name__ == '__main__':
    main()
