"""Elastic Beanstalk entry point.

EB's Python platform looks for an object called `application` in application.py
at the deployment root. We expose the Flask app under that exact name.
"""
from snapvault import create_app

application = create_app()


if __name__ == "__main__":
    application.run(host="0.0.0.0", port=5050, debug=True)
