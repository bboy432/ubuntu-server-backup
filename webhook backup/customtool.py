import requests
import json

# Your Bland.ai API Key
BLAND_AI_API_KEY = "org_974a3a18b1eb684aa9dc1a39e39c89c28527837e7262ae92fed9fe3769bee4a6a4065e5396fb6a839d7269" # <<< IMPORTANT: REPLACE THIS!

# URL for creating tools in Bland.ai
bland_tools_url = "https://api.bland.ai/v1/tools/"

# Configuration for the new custom tool
tool_payload = {
  "name": "dispatch Emergency Info Christian Technician Connection",
  "description": "Collects and sends caller's name, address, callback number, emergency description, and the chosen emergency service phone number to a webhook.",
  "speech": "Thank you. I'm now relaying this information.",
  "url": "https://tadpole-light-hugely.ngrok-free.app/webhook",
  "method": "POST",
  "headers": {},
  "query": {},
  "response": {},
  "timeout": 60000,
  "public": False,
  "body": {
    "chosen_phone": "+15313291106",
    "customer_name": "{{input.name}}",
    "system_call_id": "{{call_id}}",
    "incident_address": "{{input.full_address_string}}",
    "system_caller_id": "{{phone_number}}",
    "emergency_description_text": "{{input.emergency_description}}",
    "user_stated_callback_number": "{{input.user_stated_callback_number}}"
  },
  "input_schema": {
    "examples": {
      "user_stated_callback_number": "three eight five nine eight five seven zero six two"
    },
    "required": [
      "name",
      "full_address_string",
      "emergency_description",
      "user_stated_callback_number"
    ],
    "properties": {
      "name": {
        "type": "string",
        "description": "The full name of the person providing the information. For example, 'Alex Smith'."
      },
      "full_address_string": {
        "type": "string",
        "description": "The complete address of where the emergency is located or where assistance is needed, including street, city, state, and ZIP code. For example, '789 Pine Bluff Road, Golden, CO 80401'."
      },
      "emergency_description": {
        "type": "string",
        "description": "A clear and concise description of the emergency situation. For example, 'Reporting a hiker lost on Green Mountain trail' or 'A multi-car accident at Broadway and Baseline'."
      },
      "user_stated_callback_number": {
        "type": "string",
        "description": "The phone number explicitly provided by the user for a callback regarding this situation. Should include area code. For example, '+13035551234'."
      }
    }
  }
}

# Headers for the request to Bland.ai API
request_headers = {
    "authorization": BLAND_AI_API_KEY,
    "Content-Type": "application/json"
}

if BLAND_AI_API_KEY == "YOUR_BLAND_AI_API_KEY":
    print("WARNING: Please replace 'YOUR_BLAND_AI_API_KEY' with your actual Bland.ai API key before running.")
else:
    # Optional: Pretty print the payload to verify before sending
    print("Sending the following payload to Bland.ai tools API:")
    print(json.dumps(tool_payload, indent=2))
    print("-" * 40)

    # Make the request to Bland.ai to create the tool
    response = requests.post(bland_tools_url, json=tool_payload, headers=request_headers)

    # Print the response from Bland.ai
    print(f"Status Code from Bland.ai: {response.status_code}")
    print("Response Text from Bland.ai:")
    try:
        # Try to parse and print JSON if the response is JSON
        print(json.dumps(response.json(), indent=2))
    except requests.exceptions.JSONDecodeError:
        # If not JSON, print as plain text
        print(response.text)
