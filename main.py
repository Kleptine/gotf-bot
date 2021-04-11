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

# [START functions_slack_setup]
import calendar
import datetime
import os
import pprint
import re
import threading
import time

from flask import jsonify
from slack.signature import SignatureVerifier
from slack import WebClient
from slack.errors import SlackApiError
import gspread
import emoji
import argparse
import num2word

sheet_game_name_column = 2
sheet_icon_column = 3
sheet_nominator_name_column = 4


# [END functions_slack_setup]


# [START functions_verify_webhook]
def verify_signature(request):
    request.get_data()  # Decodes received requests into request.data

    verifier = SignatureVerifier(os.environ['SLACK_SECRET'])

    if not verifier.is_valid_request(request.data, request.headers):
        raise ValueError('Invalid request/credentials.')


# [END functions_verify_webhook]

def get_list_google_sheets(worksheet_num):
    gc = gspread.service_account("gameofthefortnight.json")
    doc = gc.open_by_url("https://docs.google.com/spreadsheets/d/17G-T9rNAo0qzrCq5ih07AxdYDmRfsIK4MKjsH4Fxp9o")
    sheet = doc.get_worksheet(worksheet_num)
    return sheet


def find_row_with_icon(sheet, icon):
    icons = sheet.col_values(sheet_icon_column)
    try:
        return icons.index(icon) + 1
    except ValueError:
        return None


def gotf(request):
    if request.method != 'POST':
        return 'Only POST requests are accepted', 405
    verify_signature(request)

    command = request.form['command']
    if command == "/nominate":
        return nominate(request)
    elif command == "/start_vote":
        return start_vote(request)
    elif command == "/call_vote":
        return call_vote(request)
    elif command == "/start_date_vote":
        return start_date_vote(request)
    # elif command == "/call_date_vote":
        # return call_vote(request)


# [START functions_slack_search]
def nominate(request):
    # parser = argparse.ArgumentParser(description='Nominate a game to game of the fortnight')
    # parser.add_argument('name', metavar='[Game Name]', type=str, help="The name of the game")
    # parser.add_argument('emoji', metavar='[Emoji]', type=str, help="A single emoji to represent the game in polls")
    # args = parser.parse_args(arguments.split(" "))

    print("Got Nominate: " + str(request.form))
    sheet = get_list_google_sheets(0)

    arguments = request.form['text'].split(" ")
    if len(arguments) < 2:
        return error_response("Incorrect command format. It should look like: \"/nominate Portal 2 :cake:\"")

    icon = arguments[-1]
    if re.search("^:.*:$", icon) is None:
        return error_response(
            "The last word must be a single emoji! Instead found: '{}', which was not an emoji.  It should look like: "
            "\"/nominate Portal 2 :cake:\"".format(icon))

    # if len(icon) != 1:
    #     return error_response(
    #         "The last word must be a single emoji! Instead found: '{}' which was too long.".format(icon))

    existing_row = find_row_with_icon(sheet, icon)
    if existing_row is not None:
        existing_game = sheet.cell(existing_row, sheet_game_name_column).value
        existing_nominator = sheet.cell(existing_row, sheet_nominator_name_column).value
        return error_response(
            "There is already a game using the emoji [{}]: \"{}\" nominated by {}".format(icon, existing_game,
                                                                                          existing_nominator))

    nominator = request.form['user_id']
    game_name = " ".join(arguments[:-1])
    if game_name == "":
        return error_response("Incorrect command format. It should look like: \"/nominate Portal 2 :cake:\"")

    # response_url = request.form['response_url']

    # Post in the main channel about the game being nominated.
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    channel_id = "C01TUKQ7XPV"  # #general

    try:
        # Get the user's name
        result = client.users_info(user=request.form['user_id'])
        print(result)
        user_display_name = result['user']['profile']['display_name']
        if user_display_name == '':
            user_display_name = result['user']['profile']['real_name']

        # Add to google sheets
        row = [game_name, icon, user_display_name, datetime.datetime.today().strftime("%m/%d/%y"), nominator]
        print("Added row to sheet:" + str(row))
        sheet.append_row(row, "RAW")

        # Call the chat.postMessage method using the WebClient
        result = client.chat_postMessage(
            channel=channel_id,
            text='{} nominated "{}" for game of the fortnight.  {}'.format(user_display_name, game_name, icon),
        )
        timestamp = result['ts']
        print("posted: " + timestamp)
        result = client.reactions_add(
            name=icon.replace(":", ""),
            channel=channel_id,
            timestamp=timestamp
        )
        print(result)

    except SlackApiError as e:
        print(f"Error posting message: {e}")

    # if response_url is not None:

    return jsonify({
        'response_type': 'ephemeral',
        'text': "Success. Thanks for the nomination!",
        'attachments': []
    })


# [START functions_slack_search]
def start_vote(request):
    # parser = argparse.ArgumentParser(description='Nominate a game to game of the fortnight')
    # parser.add_argument('name', metavar='[Game Name]', type=str, help="The name of the game")
    # parser.add_argument('emoji', metavar='[Emoji]', type=str, help="A single emoji to represent the game in polls")
    # args = parser.parse_args(arguments.split(" "))

    print("Got Start Vote Request: " + str(request.form))
    sheet = get_list_google_sheets(0)

    nominees = sheet.get_all_records()
    message = "Please vote for the next Game of the Fortnight!"
    for nominee in nominees:
        message += "\n   •  {} {}".format(nominee["Name"], nominee["Emoji"])

    # Post message
    client = WebClient(token=os.environ.get("SLACK_TOKEN"))
    channel_id = "C01TUKQ7XPV"  # #general

    result = client.chat_postMessage(
        channel=channel_id,
        text=message,
        parse="full",
        mrkdown=True
    )
    timestamp = result['ts']
    print("posted: " + timestamp)

    for nominee in nominees:
        reaction = nominee["Emoji"].replace(":", "")
        print("adding reaction: [{}]".format(reaction))
        result = client.reactions_add(
            name=reaction,
            channel=channel_id,
            timestamp=timestamp
        )
    print(result)

    # Start a new vote row in the sheet
    votes = get_list_google_sheets(1)
    row = [str(datetime.date.today()), str(timestamp)]
    print(row)
    votes.append_row(row)

    return jsonify({
        'response_type': 'ephemeral',
        'text': "Success. Started a vote!",
        'attachments': []
    })


def call_vote(request):
    print("Got Call Vote Request: " + str(request.form))

    # Find all votes without winners, look up the reaction counts.
    votes = get_list_google_sheets(1)
    for vote_row_index, row in enumerate(votes.get_all_records(numericise_ignore=['all'])):
        print(row)
        if row["Game Name"] == '':
            timestamp = row["Vote Timestamp"]
            print(timestamp)

            client = WebClient(token=os.environ.get("SLACK_TOKEN"))
            channel_id = "C01TUKQ7XPV"  # #general

            try:
                result = client.reactions_get(
                    channel=channel_id,
                    timestamp=timestamp
                )
                reactions = result['message']['reactions']

                sorted_reactions = sorted(list(reactions), key=lambda x: x['count'], reverse=True)

                winner = sorted_reactions[0]
                if len(sorted_reactions) > 1 and sorted_reactions[1]['count'] == winner['count']:
                    return error_response("There is a tie! No winner found!")

                # Find the game in the nominees list and transfer it to the votes column.
                def transfer():
                    nominees = get_list_google_sheets(0)
                    nominee_row = find_row_with_icon(nominees, ":{}:".format(winner['name']))
                    nominees_list = nominees.get_all_values()
                    src = nominees_list[nominee_row - 1][1:]
                    dst_start = votes.cell(vote_row_index + 2, 4)
                    votes.update("{}".format(dst_start.address), [src])

                    # Remove the row from nominees
                    nominees.delete_row(nominee_row)

                th = threading.Thread(target=transfer)
                th.start()

                return jsonify({
                    'response_type': 'ephemeral',
                    'text': "Success. {} wins".format(winner['name']),
                    'attachments': []
                })

                # # Post about the vote win!
                # result = client.chat_postMessage(
                #     channel=channel_id,
                #     text="",
                #     parse="full",
                #     mrkdown=True
                # )

            except SlackApiError as e:
                print(f"Error from slack api: {e}")


def start_date_vote(request):
    print("Got Start Date Vote Request: " + str(request.form))

    # Find all votes without winners, look up the reaction counts.
    votes = get_list_google_sheets(1)
    for vote_row_index, row in enumerate(votes.get_all_records(numericise_ignore=['all'])):
        print(row)
        if row["Discussion Date"] == '':
            client = WebClient(token=os.environ.get("SLACK_TOKEN"))
            channel_id = "C01TUKQ7XPV"  # #general

            try:
                date = datetime.datetime.strptime(request.form['text'], '%m/%d/%y')
                dayNumber = calendar.weekday(date.year, date.month, date.day)
                message = "Please vote for the date for the {} GOTF!".format(row["Game Name"])

                date = date - datetime.timedelta(days=dayNumber)
                reactions = []
                for i in range(0, 5):
                    day = str(date.day)
                    digit = day[-1]
                    icon = digit2word(digit)
                    reactions.append(icon)
                    message += date.strftime("\n   •  %A, %B %d  :{}:".format(icon))
                    date = date + datetime.timedelta(days=1)

                result = client.chat_postMessage(
                    channel=channel_id,
                    text=message,
                    parse="full",
                    mrkdown=True
                )
                timestamp = result['ts']

                for r in reactions:
                    print(r)
                    result = client.reactions_add(
                        name=r,
                        channel=channel_id,
                        timestamp=timestamp
                    )

                return jsonify({
                    'response_type': 'ephemeral',
                    'text': "Success.",
                    'attachments': []
                })

                # # Post about the vote win!
                # result = client.chat_postMessage(
                #     channel=channel_id,
                #     text="",
                #     parse="full",
                #     mrkdown=True
                # )

            except SlackApiError as e:
                print(f"Error from slack api: {e}")


def digit2word(digit):
    if digit == "0":
        return "zero"
    elif digit == "1":
        return "one"
    elif digit == "2":
        return "two"
    elif digit == "3":
        return "three"
    elif digit == "4":
        return "four"
    elif digit == "5":
        return "five"
    elif digit == "6":
        return "six"
    elif digit == "7":
        return "seven"
    elif digit == "8":
        return "eight"
    elif digit == "9":
        return "nine"
    return None


def error_response(error_text):
    return jsonify({
        'response_type': 'ephemeral',
        'text': 'Error: ' + error_text,
        'attachments': []
    })

# [END functions_slack_search]
