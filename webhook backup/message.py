import os
from twilio.rest import Client

account_sid ="AC0903a4f27d71f6672fb4ef47cfcaaff5"
auth_token = "744044a65f6492b3d20dd9c84537b880"
twilio_phone_number = "+12084177925"
target_phone_number = "+18017104034"

client = Client(account_sid, auth_token)

message = client.messages.create(
    body="Hello from Twilio!",
    from_=twilio_phone_number,
    to=target_phone_number,
)

print(message.sid)
