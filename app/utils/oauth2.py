from app.config.settings import settings

def get_google_auth_url():
    return f"https://accounts.google.com/o/oauth2/v2/auth?response_type=code&client_id={settings.GOOGLE_CLIENT_ID}&redirect_uri={settings.BASE_URL}/auth/google/callback&scope=openid%20email%20profile"
