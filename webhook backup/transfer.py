import subprocess
import time
import requests
import atexit
import os
import json
import platform
from flask import Flask, request, jsonify
import logging
from datetime import datetime, timedelta  # Import datetime and timedelta for timestamp formatting
from twilio.rest import Client
from twilio.twiml.voice_response import VoiceResponse, Dial, Pause # <-- ADDED for TwiML

# --- Configuration ---
FLASK_PORT = 5000  # The local port your Flask app will run on
# Path to ngrok executable.
NGROK_PATH = 'ngrok'

# --- Twilio Configuration ---
TWILIO_ACCOUNT_SID = 'AC0903a4f27d71f6672fb4ef47cfcaaff5' # Keep your actual SID
TWILIO_AUTH_TOKEN = '744044a65f6492b3d20dd9c84537b880'   # Keep your actual Auth Token
TWILIO_PHONE_NUMBER = '+12084177925'                      # Your Twilio number

# --- New Configuration for Incoming Call Transfer ---
TRANSFER_TARGET_PHONE_NUMBER = "+18017104034"  # <--- REPLACE with the number to transfer to (E.164 format)
WAIT_DURATION_SECONDS = 15  # How many seconds to wait before transferring
# --- End Configuration ---

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__)
ngrok_process = None
public_url = None # This will be set by start_ngrok

def find_ngrok_path():
    """Tries to find ngrok if it's not just 'ngrok'."""
    if NGROK_PATH == 'ngrok': # If default, try to find it
        if platform.system() == "Windows":
            common_paths = [
                os.path.join(os.environ.get("ProgramFiles", "C:\\Program Files"), "ngrok", "ngrok.exe"),
                os.path.join(os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)"), "ngrok", "ngrok.exe"),
                os.path.join(os.environ.get("LocalAppData", ""), "ngrok", "ngrok.exe"),
            ]
            for path_to_check in common_paths:
                if os.path.exists(path_to_check):
                    logging.info(f"Found ngrok at: {path_to_check}")
                    return path_to_check
            try:
                subprocess.run(['ngrok', '--version'], capture_output=True, check=True, creationflags=subprocess.CREATE_NO_WINDOW)
                return 'ngrok'
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
        else: # Linux/macOS
            try:
                result = subprocess.run(['which', 'ngrok'], capture_output=True, text=True, check=True)
                found_path = result.stdout.strip()
                if found_path:
                    logging.info(f"Found ngrok at: {found_path}")
                    return found_path
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass
    return NGROK_PATH


def start_ngrok(port):
    global ngrok_process, public_url
    try:
        if platform.system() == "Windows":
            subprocess.run(['taskkill', '/F', '/IM', 'ngrok.exe'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        else:
            subprocess.run(['pkill', 'ngrok'], stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        time.sleep(2)
    except:
        pass

    effective_ngrok_path = find_ngrok_path()
    try:
        command = [effective_ngrok_path, 'http', str(port)]
        logging.info(f"Starting ngrok with command: {' '.join(command)}")
        creationflags = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
        ngrok_process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creationflags)
        logging.info(f"ngrok process started with PID: {ngrok_process.pid}")
        time.sleep(5)

        try:
            response = requests.get("http://127.0.0.1:4040/api/tunnels", timeout=10) # Increased timeout
            response.raise_for_status()
            tunnels_data = response.json()
            https_tunnel = None
            http_tunnel = None
            for tunnel in tunnels_data.get("tunnels", []):
                if tunnel.get("proto") == "https":
                    https_tunnel = tunnel.get("public_url")
                elif tunnel.get("proto") == "http":
                    http_tunnel = tunnel.get("public_url")
            
            public_url = https_tunnel if https_tunnel else http_tunnel # Prefer https
            if not public_url:
                logging.error("ngrok API response does not contain a public URL. Tunnels data: %s", tunnels_data)
                if ngrok_process.poll() is not None:
                    _, stderr = ngrok_process.communicate()
                    logging.error(f"ngrok process terminated. Stderr: {stderr.decode(errors='ignore')}")
                return None
            return public_url
        except requests.exceptions.ConnectionError:
            logging.error("Could not connect to ngrok API at http://127.0.0.1:4040. Is ngrok running correctly?")
            if ngrok_process:
                stdout, stderr = ngrok_process.communicate(timeout=2)
                if stdout: logging.info(f"ngrok stdout: {stdout.decode(errors='ignore')}")
                if stderr: logging.error(f"ngrok stderr: {stderr.decode(errors='ignore')}")
            return None
        except requests.exceptions.RequestException as e:
            logging.error(f"Error fetching ngrok public URL: {e}")
            return None
        except json.JSONDecodeError:
            logging.error(f"Failed to decode JSON response from ngrok API. Response text: {response.text if response else 'No response'}")
            return None
    except FileNotFoundError:
        logging.error(f"ngrok command '{effective_ngrok_path}' not found. Please ensure ngrok is installed and in your PATH, or NGROK_PATH is set correctly.")
        logging.error("Download ngrok from https://ngrok.com/download")
        return None
    except Exception as e:
        logging.error(f"An unexpected error occurred while starting ngrok: {e}")
        if ngrok_process and ngrok_process.poll() is None:
            ngrok_process.terminate()
            ngrok_process.wait()
        return None

def stop_ngrok():
    global ngrok_process
    if ngrok_process and ngrok_process.poll() is None:
        logging.info("Stopping ngrok...")
        ngrok_process.terminate()
        try:
            ngrok_process.wait(timeout=5)
            logging.info("ngrok process terminated.")
        except subprocess.TimeoutExpired:
            logging.warning("ngrok process did not terminate in time, killing.")
            ngrok_process.kill()
            ngrok_process.wait()
            logging.info("ngrok process killed.")
        ngrok_process = None

atexit.register(stop_ngrok)

def format_emergency_message(data):
    message_parts = []
    if data.get('emergency_details'):
        message_parts.append(f"Emergency details: {data['emergency_details']}")
    if data.get('customer_address'):
        message_parts.append(f"Address: {data['customer_address']}")
    if data.get('system_caller_id'):
        message_parts.append(f"Caller ID: {data['system_caller_id']}")
    if data.get('user_stated_callback_number'):
        message_parts.append(f"Callback number: {data['user_stated_callback_number']}")
    return ". ".join(message_parts)

def make_emergency_call(message):
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = client.calls.create(
            twiml=f'<Response><Pause length="2"/><Say>{message}</Say></Response>',
            to='+18017104034',  # Replace with your target phone number for emergency
            from_=TWILIO_PHONE_NUMBER
        )
        logging.info(f"Emergency call initiated! Call SID: {call.sid}")
        return True
    except Exception as e:
        logging.error(f"Error making emergency call: {str(e)}")
        return False

@app.route('/webhook', methods=['POST'])
def webhook_listener():
    logging.info("\n" + "="*50 + "\nNEW WEBHOOK (generic) RECEIVED\n" + "="*50)
    logging.info(f"Request Path: {request.path}")
    log_request_details(request) # Helper function to log details
    if request.is_json:
        data = request.get_json()
        message = format_emergency_message(data)
        if message:
            make_emergency_call(message)
    logging.info("="*50 + "\n")
    return jsonify({"status": "success", "message": "Generic webhook received"}), 200

# --- NEW FLASK ROUTE FOR INCOMING TWILIO CALLS ---
@app.route("/incoming_twilio_call", methods=['POST'])
def handle_incoming_twilio_call():
    """
    Handles incoming Twilio voice calls: answers, waits, and then transfers.
    """
    logging.info("\n" + "="*50 + "\nINCOMING TWILIO CALL RECEIVED\n" + "="*50)
    log_request_details(request) # Log details of Twilio's request

    # Create a new TwiML response
    twiml_response_obj = VoiceResponse()

    # Greet the caller (this also answers the call)
    twiml_response_obj.say("Thank you for calling. Please wait while we connect you.")

    # Pause the call for the specified duration
    twiml_response_obj.pause(length=WAIT_DURATION_SECONDS)

    # Dial (transfer) to the target phone number
    # Using TWILIO_PHONE_NUMBER as the callerId for the outbound leg of the transfer
    dial = Dial(caller_id=TWILIO_PHONE_NUMBER)
    dial.number(TRANSFER_TARGET_PHONE_NUMBER)
    twiml_response_obj.append(dial)

    # Fallback message if the Dial action fails (e.g., target doesn't answer, busy)
    twiml_response_obj.say("We were unable to transfer your call at this time. Goodbye.")
    twiml_response_obj.hangup()

    logging.info(f"Responding with TwiML: {str(twiml_response_obj)}")
    logging.info("="*50 + "\n")

    # Return TwiML as XML
    return str(twiml_response_obj), 200, {'Content-Type': 'application/xml'}
# --- END OF NEW FLASK ROUTE ---

def log_request_details(req):
    """Helper function to log details of a Flask request object."""
    logging.info(f"From: {req.remote_addr}")
    logging.info("HEADERS:")
    for header, value in req.headers:
        logging.info(f"  {header}: {value}")
    logging.info("QUERY PARAMETERS:")
    for key, value in req.args.items():
        logging.info(f"  {key}: {value}")
    logging.info("FORM DATA:")
    for key, value in req.form.items(): # Twilio often sends data as form-urlencoded
        logging.info(f"  {key}: {value}")
    try:
        if req.data: # Log raw data if any
            logging.info(f"RAW DATA: {req.get_data(as_text=True)}")
        if req.is_json:
            logging.info(f"PARSED JSON: {json.dumps(req.get_json(), indent=2)}")
    except Exception as e:
        logging.warning(f"Could not log full request data: {e}")


@app.route('/', methods=['GET'])
def home():
    global public_url # Ensure we're using the global variable
    if public_url:
        return (f"Webhook listener is running.<br>"
                f"Generic POST webhook URL: {public_url}/webhook<br>"
                f"Twilio Incoming Call POST URL: {public_url}/incoming_twilio_call"), 200
    else:
        return "Webhook listener is running, but ngrok URL is not available yet. Please wait or check logs.", 200

if __name__ == '__main__':
    logging.info(f"Attempting to start ngrok for Flask app on port {FLASK_PORT}...")
    retrieved_public_url = start_ngrok(FLASK_PORT) # This sets the global public_url

    if public_url: # Check the global variable updated by start_ngrok
        logging.info(f"ngrok started successfully!")
        logging.info(f"Your generic POST webhook URL is: {public_url}/webhook")
        logging.info(f"Your Twilio Incoming Call POST URL is: {public_url}/incoming_twilio_call")
        logging.info(f"Configure the '/incoming_twilio_call' URL in your Twilio phone number settings.")
        logging.info(f"Your local Flask app is running on: http://127.0.0.1:{FLASK_PORT}")
        logging.info("Press CTRL+C to stop the server and ngrok.")

        try:
            app.run(host='0.0.0.0', port=FLASK_PORT, debug=False) # debug=False recommended for ngrok stability
        except Exception as e:
            logging.error(f"Failed to start Flask app: {e}")
        finally:
            logging.info("Flask app has stopped.")
    else:
        logging.error("Failed to start ngrok or retrieve public URL.")
        logging.error("Please check the ngrok installation and ensure it's working correctly.")
        logging.error("You might need to run 'ngrok http %s' manually in another terminal.", FLASK_PORT)
        logging.info("Exiting script.")