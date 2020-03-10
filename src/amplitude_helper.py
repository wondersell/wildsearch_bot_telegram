import json

import requests


class AmplitudeLogger:
    def __init__(self, api_key):
        self.api_key = api_key
        self.endpoint = 'https://api.amplitude.com/2/httpapi'

    def log(self, user_id, event):
        requests.post(self.endpoint, data=json.dumps({
            'api_key': self.api_key,
            'events': [
                {
                    'user_id': user_id,
                    'event_type': event,
                },
            ],
        }))
