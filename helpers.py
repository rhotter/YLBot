import csv
from googleSheetData import getData
import datetime
from dateutil import parser

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

def saveMessage(body, names, phoneNumbers):
    date = datetime.datetime.now()
    with open('static/messages.csv', 'a') as f:
        writer = csv.writer(f)
        nameText = ''
        phoneNumbersText = ''
        for name in names:
            nameText += name[0] + '___' + name[1] + '~~~' # ~~~ deliniates names, ___ deliniates first/last
        nameText = nameText[:-3]
        for phoneNumber in phoneNumbers:
            phoneNumbersText += phoneNumber + '___'
        phoneNumbersText = phoneNumbersText[:-3]
        writer.writerow([date, nameText, phoneNumbersText, body])

def saveIncomingMessage(date, firstName, lastName, phoneNumber, message):
    with open('static/incomingMessages.csv', 'a') as f:
        writer = csv.writer(f)
        writer.writerow([date, firstName, lastName, phoneNumber, message])

def getMessages():
    with open('static/messages.csv','r') as f:
        reader = csv.reader(f)
        messages = [row[0] for row in reader]
        messages.reverse()
        return messages # make messages reverse chronological

def getMessagesWithInfo():
    with open('static/messages.csv','r') as f:
        messages = list(csv.reader(f))
        messages.reverse()
    outputResponses = []
    for message in messages:
        body = message[3]
        names = message[1]
        phoneNumbers = message[2]
        date = message[0]
        names = names.split('~~~')
        names = [name.split('___') for name in names]
        phoneNumbers = phoneNumbers.split('___')

        outputResponseRow = []
        for i in range(len(names)):
            name = names[i]
            phoneNumber = phoneNumbers[i]
            outputResponseRow.append([date] + name + [phoneNumber])
        outputResponses.append(outputResponseRow)
    return outputResponses

def getIncomingMessages():
    with open("static/incomingMessages.csv","r") as f:
        messages = list(csv.reader(f))
    return messages

def getResponses():
    sentMessages = getMessagesWithInfo()
    incomingMessages = getIncomingMessages()
    print(sentMessages)
    print(incomingMessages)

    responses = sentMessages.copy()

    for message in sentMessages:
        for i in range(len(message)):
            sentMessageItems = message[i]
            sentPhoneNumber = sentMessageItems[3]
            sentDate = parser.parse(sentMessageItems[2])
            for incomingMessageItems in incomingMessages:
                incomingPhoneNumber = incomingMessageItems[3]
                incomingDate = parser.parse(incomingMessageItems[3])

    return sentMessages

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
