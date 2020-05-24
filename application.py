from flask import Flask, render_template, request, redirect
from googleSheetData import getData
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
from flask_basicauth import BasicAuth
import datetime
from flask_pymongo import PyMongo
from dateutil import parser
import csv

from secrets import MONGO_URI, BASIC_AUTH_USERNAME, BASIC_AUTH_PASSWORD

account_sid = 'ACe7102f8f5311b6df0dbda7eea122941c'
auth_token = '077cc723ee3dcd8ed2a9aecb02bc354f'
ourPhoneNumber = '+15146004534'

application = Flask(__name__)

# Mongo
application.config["MONGO_DBNAME"] = "ylbot"
application.config["MONGO_URI"] = MONGO_URI
mongo = PyMongo(application)

'''
Some mongo examples
db = mongo.db.DbName # Will create if doesn't exist
db.insert({'name': 'Hello','language': 'English'}) # create document

# query
user = db.find_one({'name': 'Hello'}) # convert to python dictionary, returns 1
print(user['language'])

# change
user['language'] = 'French'
db.save(john)

# delete
user = db.find_one({'name': 'Hello'})
db.remove(user)
'''

# Basic authentification
application.config['BASIC_AUTH_USERNAME'] = BASIC_AUTH_USERNAME
application.config['BASIC_AUTH_PASSWORD'] = BASIC_AUTH_PASSWORD

basic_auth = BasicAuth(application)

''' Functions '''
def saveMessage(body, people):
    # {'date': date, 'body': body, 'people': [{'firstName':},},]
    date = datetime.datetime.now()
    messages = mongo.db.messages
    messages.insert({'date': date, 'body': body, 'people': people})

def saveIncomingMessage(data):
    # {'date': currentDate, 'firstName': firstName, 'lastName': lastName, 'phoneNumber': phoneNumber, 'body': body}
    incomingMessages = mongo.db.incomingMessages
    incomingMessages.insert(data)

def getMessages():
    messages = mongo.db.messages
    allMessages = messages.find()

    return [message['body'] for message in allMessages]

def findPersonInIncomingMessages(person, matchedIncomingMessages):
    # This function could be improved for better speed
    # See if person is in matchedIncomingMessages and get their last reply

    for m in matchedIncomingMessages:
        if person['phoneNumber'] == m['phoneNumber']:
            return m['body']
    return None

def getResponses():
    # return a list of dictionaries with status for each person
    sentMessages = mongo.db.messages.find().sort([('date',-1)])
    sentMessagesCursor = mongo.db.messages
    incomingMessages = mongo.db.incomingMessages
    responses = []
    for m in sentMessages:
        messageResponses = []
        date = m['date']
        print(m['body'], str(date))
        people = m['people']
        for person in people:
            # oldDate: the date of the last message (smallest thatDate where thatDate > date) to this person
            oldDate = sentMessagesCursor.find({'date': {'$gt': date}, 'people.phoneNumber': person['phoneNumber']})
            oldDate = list(oldDate.sort([('date',1)]))
            if len(oldDate) < 1:
                oldDate = datetime.datetime(2400,1,1)
            else:
                oldDate = oldDate[0]

            matchedIncomingMessages = incomingMessages.find({'date': {'$gt': date,'$lt': oldDate}, 'phoneNumber': person['phoneNumber']})
            matchedIncomingMessages = list(matchedIncomingMessages.sort([('date',-1)]))

            reply = findPersonInIncomingMessages(person,matchedIncomingMessages)
            p = person.copy()
            p['reply'] = reply
            messageResponses.append(p)
        formattedDate = date.strftime("%b. ") + str(int(date.strftime("%d"))) + date.strftime(", %Y")
        formattedDate = formattedDate.upper()
        responses.append({'body': m['body'], 'date': formattedDate,'responses': messageResponses})
    return responses

def getPerson(phoneNumber):
    values = getData()
    phoneNumberCol = 2
    for val in values:
        if twilioedNumber(val[phoneNumberCol]) == phoneNumber:
            firstName = val[0]
            lastName = val[1]
            return firstName, lastName
    return None, None

def twilioedNumber(phoneNumber):
    phoneNumber = '+' + phoneNumber.replace(' ','')
    return phoneNumber

# Home page
@application.route("/")
@basic_auth.required
def index():
    return render_template("index.html",values=getData(),messages=getMessages()[-5:])

# View responses
@application.route("/responses")
@basic_auth.required
def responses():
    responses = getResponses()
    return render_template("responses.html", responses=responses)

# Send messages
@application.route("/send", methods=["POST"])

def send():
    body = request.form.get("body")
    imageURL = request.form.get("imageURL")
    text = request.form.getlist("checked")
    splitText = [t.split('###') for t in text]

    client = Client(account_sid, auth_token)

    people = []
    phoneNumbers = []
    for s in splitText:
        firstName = s[0]
        lastName = s[1]
        personalBody = body.replace('#NAME',firstName)
        phoneNumber = twilioedNumber(s[2])
        people.append({'firstName': firstName, 'lastName': lastName, 'phoneNumber': phoneNumber})
        message = client.messages.create(body=personalBody,from_=ourPhoneNumber,status_callback="http://0f005a7c.ngrok.io/callback",to=phoneNumber)
        if len(imageURL) > 0:
            message = client.messages.create(from_=ourPhoneNumber,to=phoneNumber,media_url=imageURL)

    saveMessage(body,people)
    return render_template("sent.html")

# Responding to messages
@application.route("/sms", methods=['GET', 'POST'])
def sms_ahoy_reply():
    # Should check to see their reply before storing, and respond intelligently
    body = request.values.get('Body', None)
    phoneNumber = request.values.get('From', None)
    resp = MessagingResponse()

    currentDate = datetime.datetime.now()
    firstName,lastName = getPerson(phoneNumber)
    if (firstName,lastName) == (None, None):
        resp.message("I don't seem to find your phone # in our member directory. Please contact someone from the YL Team.")
        return str(resp)

    response = body.upper()
    if response == 'COMING':
        saveIncomingMessage({'date': currentDate, 'firstName': firstName, 'lastName': lastName, 'phoneNumber': phoneNumber, 'body': body})
        resp.message("Thanks {}! See you there!".format(firstName))
    elif response == 'NEXT TIME':
        saveIncomingMessage({'date': currentDate, 'firstName': firstName, 'lastName': lastName, 'phoneNumber': phoneNumber, 'body': body})
        resp.message("😢")
        resp.message("Hope to see you next time!")
    else:
        resp.message("I didn't quite get that. Please respond with either \"Coming\" or \"Next time\"")
    return str(resp)

@application.route("/callback", methods=['POST'])
def callback():
    smsStatus = request.values.get('SmsStatus',None)
    print(smsStatus)
    return ('', 204)

if __name__ == "__main__":
    application.run(debug=True, ssl_context='adhoc')
