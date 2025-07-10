from mail_sender import send_email

def read_recipients(file_path):
    with open(file_path, 'r') as f:
        # Remove empty lines and comments
        return [line.strip() for line in f if line.strip() and not line.startswith('#')]

def send_to_all(subject, body):
    recipients = read_recipients('recipients.txt')
    for recipient in recipients:
        send_email(recipient, subject, body)


