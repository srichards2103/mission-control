"""Settings for the test suite: `config.settings` with a test-only SECRET_KEY.

`config.settings` fails closed -- `DEBUG` defaults to False, and with DEBUG off there
is no fallback `SECRET_KEY`, so a deploy that forgets to set one crashes rather than
silently signing JWTs with the publicly-committed dev key. That makes the test process
just another environment that has to supply its own key. Supplying it here (rather than
defaulting `DEBUG` back to True) keeps the suite running in the same production-shaped
configuration a deploy uses, including the JSON 404/500 handlers, which Django only
reaches when DEBUG is off.

`os.environ.setdefault`, not a plain assignment: an explicitly exported SECRET_KEY or
DEBUG still wins, so this module can never mask a real environment.
"""

import os

# >=32 bytes, so HS256 signing doesn't emit PyJWT's InsecureKeyLengthWarning.
os.environ.setdefault("SECRET_KEY", "test-only-key-never-used-outside-pytest")

from config.settings import *  # noqa: E402, F403
