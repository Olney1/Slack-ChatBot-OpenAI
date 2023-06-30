"""A quick script to find your Slack bot user id - needed for the Fast API app in main.py."""

from slack_sdk import WebClient
from dotenv import load_dotenv
import os

# load environment variables
load_dotenv()

# get the bot token from the environment variables
slack_token = os.getenv("SLACK_TOKEN")

# create a Web API client with the bot token
client = WebClient(token=slack_token)

# call the auth.test method and get the user_id
response = client.api_call("auth.test")

# print the user_id
print(response.get('user_id'))