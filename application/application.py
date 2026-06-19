"""Elastic Beanstalk / Gunicorn entry point.

The EB Python platform (and the Procfile) look for a WSGI callable named
`application`, so we expose the Flask app under exactly that name.
"""
import os

from app import create_app

application = create_app()


if __name__ == "__main__":
    # Local development server. Production uses Gunicorn (see Procfile).
    port = int(os.environ.get("PORT", "5000"))
    application.run(host="0.0.0.0", port=port, debug=True, use_reloader=False)
