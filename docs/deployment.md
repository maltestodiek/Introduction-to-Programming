# Streamlit Community Cloud deployment

Deploy app.py from the first-feature branch with Python 3.13. uv.lock and pyproject.toml define dependencies.

Set SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY and APP_URL in Streamlit Advanced settings -> Secrets. APP_URL must be the assigned HTTPS application URL. Never commit secrets.toml, database passwords, service-role keys or local data.

In Supabase Authentication -> URL Configuration, set Site URL to the public APP_URL and allow both that exact URL and http://localhost:8501 for local development.

Check the deployed sign-in screen, invalid input, and signed-out access. The account owner should test signup email confirmation, password reset, and their saved profile.
