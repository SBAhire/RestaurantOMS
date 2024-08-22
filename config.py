class Config:
    SECRET_KEY = 'your_secret_key'  # Replace with your secret key
    SQLALCHEMY_DATABASE_URI = 'postgresql://username:password@localhost/restaurant_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USERNAME = 'your-email@gmail.com'
    MAIL_PASSWORD = 'your-email-password'
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
