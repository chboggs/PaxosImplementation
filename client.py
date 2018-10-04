import json
import multiprocessing
import random
import socket
import time
import consts as cs
from random_words import RandomWords


class Client(multiprocessing.Process):
    def __init__(self, clientID, configFile):
        super(Client, self).__init__()
        self.clientID = clientID
        with open(configFile, 'r') as fd:
            self.config = json.load(fd)
        self.host = self.config[cs.CLIENT_HOSTS_KEY][clientID]
        self.port = self.config[cs.CLIENT_PORTS_KEY][clientID]
        self.sequenceNum = 0
        self.viewIdea = 0
        self.wordGen = RandomWords()
        self.currentMessage = None
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.settimeout(self.config[cs.CLIENT_TIME_KEY])
        self.socket.bind((self.host, self.port))
        self.socket.listen(500)


    def run(self):
        # Send requests consectutively until terminated
        while True:
            self.sendRequest()
            self.waitResponse()


    def sendRequest(self):
        # Create and send a message to the believed leader
        if self.currentMessage is None:
            self.currentMessage = self.createMessage()
        newSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        newSocket.connect((self.config[cs.REPLICA_HOSTS_KEY][self.viewIdea],
                           self.config[cs.REPLICA_PORTS_KEY][self.viewIdea]))
        if random.random() >= self.config[cs.LOSS_RATE_KEY]:
            newSocket.send(json.dumps(self.currentMessage).encode())
        newSocket.close()


    def waitResponse(self):
        try:
            connection, clientAddr = self.socket.accept()
            message = json.loads(connection.recv(8192).decode())
            if message[cs.MESSAGE_TYPE_KEY] == cs.REPLICA_NOT_LEADER:
                # The leader must have changed in the meantime
                self.viewIdea = (self.viewIdea + 1) % self.config[cs.NUM_REPLICAS_KEY]
            elif message[cs.MESSAGE_TYPE_KEY] == cs.REPLICA_REQUEST_PROCESSED:
                # Cool we got the request done!
                self.currentMessage = None
        except socket.timeout:
            # Either a message was lost or the leader is dead
            self.viewIdea = (self.viewIdea + 1) % self.config[cs.NUM_REPLICAS_KEY]


    def createMessage(self):
        self.sequenceNum += 1
        message = {}
        text = ' '.join(self.wordGen.random_words(count=5)) + '.'
        message[cs.MESSAGE_TYPE_KEY] = cs.CLIENT_REQUEST
        message[cs.CLIENT_ID_KEY] = self.clientID
        message[cs.CLIENT_SEQNO_KEY] = self.sequenceNum
        message[cs.CLIENT_CONTENT_KEY] = text
        return message

