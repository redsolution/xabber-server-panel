from acertmgr.modes.webdir import HTTPChallengeHandler
from acertmgr import tools

from django.conf import settings

import requests


class ChallengeHandler(HTTPChallengeHandler):

    @staticmethod
    def get_challenge_type():
        return "dns-01"

    def create_challenge(self, domain, thumbprint, token):
        txtvalue = self._determine_txtvalue(thumbprint, token)

        data = {"domain": domain, "challenge": txtvalue}

        # Send a POST request to create the challenge
        response = requests.post(settings.CHALLENGE_URL, json=data)

        # Check if the request was successful
        if response.status_code == 200:
            print("Challenge created successfully.")
        else:
            e = "Failed to create challenge. Status: %s. Reason: %s" % (response.status_code, response.reason)
            print(e)
            raise Exception(e)

    @staticmethod
    def _determine_txtvalue(thumbprint, token):
        return tools.bytes_to_base64url(tools.hash_of_str("{0}.{1}".format(token, thumbprint)))

    def destroy_challenge(self, domain, thumbprint, token):
        # Prepare the data for the DELETE request
        txtvalue = self._determine_txtvalue(thumbprint, token)

        data = {"domain": domain, "challenge": txtvalue}

        # Send a DELETE request to destroy the challenge
        response = requests.delete(settings.CHALLENGE_URL, json=data)

        # Check if the request was successful
        if response.status_code == 200:
            print("Challenge destroyed successfully.")
        else:
            print("Failed to destroy challenge. Status: %s. Reason: %s" % (response.status_code, response.reason))

    def start_challenge(self, domain, thumbprint, token):
        pass