# Copyright 2018, Google, LLC.
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import time

import googleapiclient.discovery
import mock
import pytest
from slack.signature import SignatureVerifier

import main


class Request(object):
    def __init__(self, data='', headers={}):
        self.data = data
        self.headers = headers

    def get_data(self):
        return self.data


request = Request()
request.form = {
    'text': '4/26/21',
    'user_name': 'kleptine',
    'user_id': 'U01TUKQ6SAF'
}

request.data = json.dumps(request.form)

now = str(int(time.time()))
verifier = SignatureVerifier(os.environ['SLACK_SECRET'])
test_signature = verifier.generate_signature(
    timestamp=now,
    body=request.data
)

request.method = 'POST'
request.headers = {
    'X-Slack-Request-Timestamp': now,
    'X-Slack-Signature': test_signature
}

with mock.patch('main.jsonify', side_effect=json.dumps):
    response = main.call_vote(request)

print(response)
