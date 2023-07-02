import openai
from fastapi import FastAPI, Request
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from pydantic import BaseModel
from dotenv import load_dotenv
import os
import logging
import asyncio

logging.basicConfig(level=logging.INFO)

load_dotenv()  # take environment variables from .env.

# Access the Open API key from the environment variables
openai.api_key = os.getenv("API_KEY")

# Initialize a Web API client
slack_token = os.getenv("SLACK_TOKEN")
client = WebClient(token=slack_token)

app = FastAPI()

# Store processed events
processed_events = set()

class Slack(BaseModel):
    user: str
    channel_id: str

# Create a dictionary to store the conversation histories
conversation_histories = {}

BOT_USER_ID = os.getenv("BOT_USER_ID")  # Get the bot user_id from your environment variables

@app.post("/slack/events")
async def slack_events(request: Request):
    slack_event = await request.json()
    logging.info(f"Received event: {slack_event}")

    if 'challenge' in slack_event:
        return {"challenge": slack_event['challenge']}

    # Verify that the post request is only coming from Slack. This does not verify the specfic token so this block can be upgraded for security.
    if slack_event.get('token'):
        slack_verification_token = slack_event.get('token')
        print(f'Slack event token: {slack_verification_token}')

        if 'event' in slack_event:
            event = slack_event['event']
            event_id = slack_event.get('event_id', '')  # Accessing event_id directly from slack_event

            if event_id in processed_events:
                logging.info(f'Duplicate event received: {event_id}')
                return {"status": "ok"}

            processed_events.add(event_id)
            logging.info(f'Processing event: {event_id}')

            if event.get('type') != 'message' or event.get('subtype') in ['bot_message', 'message_deleted', 'message_changed'] or event.get('user') == BOT_USER_ID:
                logging.info(f"Ignoring event: {event}")
                return {"status": "ok"}

            user_input = event.get('text', '')
            channel_id = event.get('channel', '')
            ts = event.get('ts', '')

            if user_input:
                logging.info(f"Processing event: user_input={user_input}, channel_id={channel_id}")
                await process_event(user_input, channel_id, ts)
                
        return {"status": "ok"}
        
    else:
        return {"error": "Invalid token"}


async def process_event(user_input: str, channel_id: str, ts: str):
    logging.info(f"Triggered process_event: user_input={user_input}, channel_id={channel_id}, ts={ts}")
    await get_message(user_input, channel_id)

async def get_message(user_input: str, channel_id: str):
    if channel_id not in conversation_histories:
        conversation_histories[channel_id] = []
    
    conversation_history = conversation_histories[channel_id]

    context = """
    You are a chatbot specialized in tech support for our company *** Please do not ask for screenshots or images.
    Each user will be using the latest *** operating system and the latest *** laptop is always the device being used. 
    Our company *** uses Microsoft Office applications for *** such as Teams, Excel, Word, Powerpoint and Outlook. 
    Our company *** also uses Google Workspace for non-Microsoft applications for Google Drive and Google Sheets. 
    We don't use any other browser other than Google Chrome to sign into our company applications using Google Single Sign-On (SSO).
    You should be proficient in diagnosing and troubleshooting software issues, 
    hardware issues and issues with peripheral devices connecting to the latest *** laptop.
    Our customer service team, IT team and IT Support team are called ***. They can only be reached via Slack at: ***
    For dedicated support, or questions outside of these topics, please contact ***
    If you think that a reboot/restart is needed, please explain clearly how this can help fix the user issue in detail.
    You should also be capable of addressing network and connectivity issues, providing guidance on *** security and privacy features, 
    helping with data management and navigating through system settings for application permissions and software updates. 
    Additionally, you have knowledge about commonly used productivity applications including Zoom, Slack, TeamViewer and 1Password.
    Please keep the conversation focused on these topics.
    """

    try:
        conversation_history.append(f"User: {user_input}")
        conversation_history_with_context = [context] + conversation_history

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt="\n".join(conversation_history_with_context) + "\nChatbot:",
            temperature=0,
            max_tokens=150,
            top_p=1,
            frequency_penalty=0,
            presence_penalty=0,
            stop=["\n"],
        )

        chatbot_response = response.choices[0].text.strip()
        conversation_history.append(f"Chatbot: {chatbot_response}")

        logging.info(f"Sending message: {chatbot_response}")

        # Add a delay before bot sends a response
        await asyncio.sleep(5)

        client.chat_postMessage(channel=channel_id, text=chatbot_response)

    except Exception as e:
        print(f"Error: {e}")
        client.chat_postMessage(channel=channel_id, text=str(e))

    return {"message": "processed"}