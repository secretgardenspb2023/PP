"""django-axes helper: extract the username for lockout tracking.

Our login view sends a JSON body (field ``email``) and calls ``authenticate()``
with ``username=<email>``. django-axes by default reads ``request.POST`` which is
empty for JSON requests, so we read the username from the authenticate
credentials instead (AXES_USERNAME_CALLABLE).
"""


def get_username(request, credentials):
    if credentials:
        return credentials.get("username") or credentials.get("email")
    return None
