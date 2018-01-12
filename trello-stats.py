#!/usr/bin/env python

import os, json, requests, sys, argparse
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta

TRELLO_ORG_NAME = 'redhatcop'
TRELLO_API_KEY_NAME = 'TRELLO_API_KEY'
TRELLO_API_TOKEN_NAME = 'TRELLO_API_TOKEN'
DEFAULT_START_DATE_MONTH = '03'
DEFAULT_START_DATE_DAY = '01'

# Search for cards that are done and have been modified in the past 30 days
TRELLO_SEARCH_QUERY = 'list:Done edited:{0}'

def valid_date(s):
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        msg = "Not a valid date: '{0}'.".format(s)
        raise argparse.ArgumentTypeError(msg)

def generate_start_date():
    today_date = datetime.now()
    target_start_date = datetime.strptime("{0}-{1}-{02}".format(today_date.year, DEFAULT_START_DATE_MONTH, DEFAULT_START_DATE_DAY), "%Y-%m-%d")

    if target_start_date.month < DEFAULT_START_DATE_MONTH:
        target_start_date = target_start_date - relativedelta(years=1)

    return target_start_date

def get_org_id(session):
    
    org_request = session.get("https://api.trello.com/1/organizations/{0}".format(TRELLO_ORG_NAME))
    org_request.raise_for_status()

    return org_request.json()

def search_cards(session, org_id, query):
    print query
    card_request = session.get("https://api.trello.com/1/search", params={'query': query, 'idOrganizations': org_id, 'card_fields': 'name,idMembers', 'board_fields': 'name,idOrganization', 'card_board': 'true', 'cards_limit': 1000})
    card_request.raise_for_status()

    return card_request.json()

def get_member(session, member_id):
    member_request = session.get("https://api.trello.com/1/members/{0}".format(member_id))
    member_request.raise_for_status()

    return member_request.json()

def encode_text(text):
    if text:
        return text.encode("utf-8")

    return text


trello_api_key = os.environ.get(TRELLO_API_KEY_NAME)
trello_api_token = os.environ.get(TRELLO_API_TOKEN_NAME)


if not trello_api_key or not trello_api_token:
    print "Error: Trello API Key and API Token are Required!"
    sys.exit(1)

parser = argparse.ArgumentParser(description='Gather Trello Statistics.')
parser.add_argument("-s","--start-date", help="The start date to query from", type=valid_date)
args = parser.parse_args()

start_date = args.start_date

if start_date is None:
    start_date = generate_start_date()

days = (datetime.now() - start_date).days

session = requests.Session()
session.params = {
    'key': trello_api_key,
    'token': trello_api_token,
}

org_response = get_org_id(session)
org_id = org_response['id']

resp_cards = search_cards(session, org_id, TRELLO_SEARCH_QUERY.format(days))

cards = {}
members_cards = {}

for card in resp_cards['cards']:
    
    if not card['board']['idOrganization'] or card['board']['idOrganization'] != org_id:
        continue 

    card_id = card['id']
    cards[card_id] = card

    if 'idMembers' in card:
        for member in card['idMembers']:
           
            member_id = member

            if member_id not in members_cards:
                member_cards = []
            else:
                member_cards = members_cards[member_id]
            
            member_cards.append(card_id)

            members_cards[member_id] = member_cards

print "=== Statistics for Trello Team '{0}' ====\n".format(encode_text(org_response['displayName']) if 'displayName' in org_response else encode_text(org_response['name']))
for key, value in members_cards.iteritems():
        member = get_member(session, key)
        print "{0} has {1} cards".format(encode_text(member['username']), len(value))
        for card in value:
            print "   - Board: {0} | Card: {1}".format(encode_text(cards[card]['board']['name']), encode_text(cards[card]['name']))