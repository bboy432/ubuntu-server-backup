import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(level=logging.INFO)

# Static credentials
SENDER_EMAIL = "emergency.noreply.axiom@gmail.com"
APP_PASSWORD = "zfwa ngyk hwst szgo"

def send_email(recipient_email, subject, body, debug=False):
    try:
        logging.info(f"Attempting to send email to: {recipient_email}")
        
        # Create message container
        message = MIMEMultipart()
        message['From'] = SENDER_EMAIL
        message['To'] = recipient_email
        message['Subject'] = subject

        # Add body to email
        message.attach(MIMEText(body, 'plain'))

        if debug:
            logging.info(f"Email Content:\nTo: {recipient_email}\nSubject: {subject}\nBody: {body}")
        
        # Create SMTP session with debug mode
        server = smtplib.SMTP('smtp.gmail.com', 587)
        if debug:
            server.set_debuglevel(1)
        server.starttls()
        
        # Login to the server
        server.login(SENDER_EMAIL, APP_PASSWORD)

        # Send email
        text = message.as_string()
        server.sendmail(SENDER_EMAIL, recipient_email, text)
        
        logging.info("Email sent successfully!")
        return True

    except Exception as e:
        logging.error(f"Error sending email: {str(e)}")
        return False
    
    finally:
        server.quit()