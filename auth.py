"""Per-browser-session Supabase authentication; no cached global clients."""
from dataclasses import dataclass
from logic import validate_email, validate_username

@dataclass
class Result:
    status: str
    message: str

class AuthService:
    def __init__(self,client,app_url="http://localhost:8501"):
        self.app_url=app_url.rstrip("/")
        self.client=client
        self.user=None
        self.recovery_verified=False

    def sign_up(self,email,password,confirmation,username=None,invite_token=None):
        try:
            email=validate_email(email)
            if len(password)<8: raise ValueError("Use a password with at least 8 characters.")
            if password!=confirmation: raise ValueError("The passwords do not match.")
            if username is not None: username=validate_username(username)
            redirect=self.app_url
            if invite_token:
                from logic import invitation_url
                redirect=invitation_url(self.app_url,invite_token)
        except ValueError as exc:
            return Result("invalid_input",str(exc))
        try:
            credentials={"email":email,"password":password,
                         "options":{"email_redirect_to":redirect}}
            if username: credentials["options"]["data"]={"username":username}
            self.client.auth.sign_up(credentials)
            self.user=None
            return Result("check_email","Check your inbox to confirm your email, then return here to sign in.")
        except Exception:
            self.user=None
            return Result("error","Could not create the account. Check your details or try again later.")

    def sign_in(self,email,password):
        self.user=None
        try:
            email=validate_email(email)
            if not password: raise ValueError("Enter your password.")
        except ValueError as exc:
            return Result("invalid_input",str(exc))
        try:
            response=self.client.auth.sign_in_with_password({"email":email,"password":password})
            if not response.session: raise ValueError("No session")
            self.user=self.client.auth.get_user().user
            if not self.user: raise ValueError("No verified user")
            return Result("signed_in","Welcome back.")
        except Exception:
            self.user=None
            return Result("error","Unable to sign in. Check your credentials, confirm your email, or try again shortly.")

    def verify(self):
        if not self.user: return False
        try:
            self.user=self.client.auth.get_user().user
            return self.user is not None
        except Exception:
            self.user=None
            return False

    def sign_out(self):
        try:
            self.client.auth.sign_out({"scope":"local"})
            return Result("signed_out","You are signed out.")
        except Exception:
            return Result("signed_out","Signed out of this app. Remote sign-out could not be confirmed.")
        finally:
            self.user=None
            self.recovery_verified=False

    def request_password_reset(self,email):
        try: email=validate_email(email)
        except ValueError as exc: return Result("invalid_input",str(exc))
        try:
            self.client.auth.reset_password_for_email(email,{"redirect_to":self.app_url})
            return Result("check_email","If an account exists for this email, you’ll receive a password reset link. Check your inbox and spam folder.")
        except Exception:
            return Result("error","Could not send the reset email. Please try again shortly.")

    def begin_recovery(self,data):
        self.user=None
        self.recovery_verified=False
        try:
            if data.get("type")!="recovery" or not data.get("access_token") or not data.get("refresh_token"):
                raise ValueError("Invalid recovery link")
            self.client.auth.set_session(data["access_token"],data["refresh_token"])
            user=self.client.auth.get_user().user
            if not user:raise ValueError("No verified identity")
            self.recovery_verified=True
            return Result("recovery_ready","Choose a new password.")
        except Exception:
            return Result("error","This reset link is invalid or expired. Request a new link below.")

    def update_password(self,password,confirmation):
        if not self.recovery_verified:
            return Result("error","Open a valid password reset link first.")
        if len(password)<8:return Result("invalid_input","Use a password with at least 8 characters.")
        if password!=confirmation:return Result("invalid_input","The passwords do not match.")
        try:
            if not self.client.auth.get_user().user:raise ValueError("Expired session")
            self.client.auth.update_user({"password":password})
        except Exception:
            return Result("error","Could not update your password. Try again, or request a new reset link.")
        self.recovery_verified=False
        self.sign_out()
        return Result("password_updated","Your password has been updated. Sign in with your new password.")
