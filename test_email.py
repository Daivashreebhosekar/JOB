import smtplib
from email.mime.text import MIMEText

# change these
FROM_EMAIL = "yourgmail@gmail.com"   # your Gmail
TO_EMAIL = "yourgmail@gmail.com"     # can send to yourself for testing
APP_PASSWORD = "your-16-digit-app-password"  # paste the app password here

def send_test_email():
    subject = "✅ Test Email from Python"
    body = "Hey! This is a test email sent using Gmail + Python + App Password."
    
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL

    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(FROM_EMAIL, APP_PASSWORD)
        server.sendmail(FROM_EMAIL, TO_EMAIL, msg.as_string())
        server.quit()
        print("✅ Test email sent successfully!")
    except Exception as e:
        print("❌ Something went wrong:", e)

if __name__ == "__main__":
    send_test_email()
