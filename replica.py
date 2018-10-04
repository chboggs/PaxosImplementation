import json
import multiprocessing
import threading
import random
import socket
import time
import consts as cs


class Replica(multiprocessing.Process):
    def __init__(self, replicaID, configFile):
        super(Replica, self).__init__()
        self.replicaID = replicaID
        with open(configFile, 'r') as fd:
            self.config = json.load(fd)
        self.host = self.config[cs.REPLICA_HOSTS_KEY][replicaID]
        self.port = self.config[cs.REPLICA_PORTS_KEY][replicaID]
        self.viewNum = 0
        self.amLeader = (self.replicaID == 0)
        self.confirmedLeader = False
        self.replica_hbs = {}
        for i in range(self.config[cs.NUM_REPLICAS_KEY]):
            if i == self.replicaID:
                continue
            self.replica_hbs[i] = time.time()
        self.committedSeqs = set()
        self.deadReplicas = set()
        self.numPledges = 0
        self.pledgeAccepts = []
        self.sequenceNum = -1
        self.acceptLog = {}
        self.nextCommit = 0
        self.logFilename = 'logs/replicaLog_{}.txt'.format(replicaID)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.bind((self.host, self.port))
        self.socket.listen(1000)
        self.currentMessage = None


    def run(self):
        # Start by initializing the first leader
        if self.amLeader is True:
            self.sendLeaderMessage()
        hb_thread = threading.Thread(target=self.heatbeatThread)
        hb_thread.start()
        checking_leading_failure_thread = threading.Thread(target=self.checkHeartbeats)
        checking_leading_failure_thread.start()
        # Accept indefinitely
        while True:
            # Await incoming connections on the socket
            connection, clientAddr = self.socket.accept()
            # self.currentMessage = json.loads(connection.recv(8192).decode())
            try:
                self.processMessage(json.loads(connection.recv(8192).decode()))
                connection.close()
            except:
                continue


    def broadcastReplicas(self, message):
        messageBin = json.dumps(message).encode()
        # Send the message to every other replica
        for i in range(self.config[cs.NUM_REPLICAS_KEY]):
            if i == self.replicaID or i in self.deadReplicas:
                continue
            if random.random() >= self.config[cs.LOSS_RATE_KEY]:
                try:
                    newSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    newSock.connect((self.config[cs.REPLICA_HOSTS_KEY][i],
                                     self.config[cs.REPLICA_PORTS_KEY][i]))
                    newSock.send(messageBin)
                    newSock.close()
                except:
                    continue


    def heatbeatThread(self):
        while True:
            message = {}
            message[cs.MESSAGE_TYPE_KEY] = cs.REPLICA_HEARTBEAT
            message[cs.REPLICA_ID] = self.replicaID
            self.broadcastReplicas(message)
            time.sleep(2)


    def checkHeartbeats(self):
        while True:
            time.sleep(8)
            leaderID = self.viewNum % self.config[cs.NUM_REPLICAS_KEY]
            if leaderID == self.replicaID:
                continue
            if time.time() - self.replica_hbs[leaderID] >= self.config[cs.LIVE_WINDOW_KEY]:
                self.deadReplicas.add(leaderID)
                self.proposeLeader()


    def proposeLeader(self):
        self.viewNum += 1
        leaderID = self.viewNum % self.config[cs.NUM_REPLICAS_KEY]
        if leaderID == self.replicaID:
            # I am now the leader
            self.amLeader = True
            self.sendLeaderMessage()


    def sendLeaderMessage(self):
        # Create a new "I am leader" message and broadcast it
        message = {}
        message[cs.MESSAGE_TYPE_KEY] = cs.REPLICA_I_AM_LEADER
        message[cs.REPLICA_VIEW_KEY] = self.viewNum
        self.broadcastReplicas(message)


    def processMessage(self, message):
        # The message is a replica heartbeat
        if message[cs.MESSAGE_TYPE_KEY] == cs.REPLICA_HEARTBEAT:
            self.processHeartbeatReceive(message)
            return
        self.currentMessage = message
        # The message is a request from the client
        if self.currentMessage[cs.MESSAGE_TYPE_KEY] == cs.CLIENT_REQUEST:
            if self.confirmedLeader is True:
                self.processClientCommand()
            else:
                # Not a confirmed leader, too bad, ignore it
                self.sendNotLeaderMessage()
        # The message is a pledege from another replica
        elif self.currentMessage[cs.MESSAGE_TYPE_KEY] == cs.REPLICA_YOU_ARE_LEADER:
            self.processReplicaPledge()
        # The message is an "I am leader" request
        elif self.currentMessage[cs.MESSAGE_TYPE_KEY] == cs.REPLICA_I_AM_LEADER:
            self.processNewLeader()
        # The message is a new command to do
        elif self.currentMessage[cs.MESSAGE_TYPE_KEY] == cs.REPLICA_COMMAND:
            if self.currentMessage[cs.REPLICA_VIEW_KEY] == self.viewNum:
                # The command came from the leader
                self.processReplicaCommand()
            else:
                # Ignore message from old views
                pass
        # The message is an accept from a different replica
        elif self.currentMessage[cs.MESSAGE_TYPE_KEY] == cs.REPLICA_ACCEPT:
            self.processReplicaAccept()
        # The message is telling the replica to ignore a slot
        elif self.currentMessage[cs.MESSAGE_TYPE_KEY] == cs.REPLICA_IGNORE_SLOT:
            self.processIgnoreSlot()
        # The message is a replica heartbeat
        elif self.currentMessage[cs.MESSAGE_TYPE_KEY] == cs.REPLICA_HEARTBEAT:
            self.processHeartbeatReceive()
        else:
            # Who knows?
            pass


    def processClientCommand(self):
        # Record the client request locally
        self.sequenceNum += 1
        if self.config[cs.SKIP_SLOT_KEY] is True and random.random() >= 0.8:
            self.sequenceNum += 1
        self.acceptLog[self.sequenceNum] = {'MESSAGE': self.currentMessage,
                                            'COUNT': 1}
        # Send a new message to the replicas to initiate the command
        message = {}
        message[cs.MESSAGE_TYPE_KEY] = cs.REPLICA_COMMAND
        message[cs.REPLICA_VIEW_KEY] = self.viewNum
        message[cs.REPLICA_SEQNO_KEY] = self.sequenceNum
        message[cs.REPLICA_MESSAGE_KEY] = self.currentMessage
        self.broadcastReplicas(message)


    def processHeartbeatReceive(self, message):
        sending_replica = message[cs.REPLICA_ID]
        self.replica_hbs[sending_replica] =  time.time()


    def sendNotLeaderMessage(self):
        # Send a message to the client that I'm not the leader
        # and they should try someone else
        message = {}
        message[cs.MESSAGE_TYPE_KEY] = cs.REPLICA_NOT_LEADER
        messageBin = json.dumps(message).encode()
        if random.random() >= self.config[cs.LOSS_RATE_KEY]:
            newSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            newSock.connect((self.config[cs.CLIENT_HOSTS_KEY][self.currentMessage[cs.CLIENT_ID_KEY]],
                             self.config[cs.CLIENT_PORTS_KEY][self.currentMessage[cs.CLIENT_ID_KEY]]))
            newSock.send(messageBin)
            newSock.close()


    def processReplicaPledge(self):
        self.numPledges += 1
        self.pledgeAccepts.append(self.currentMessage[cs.REPLICA_ACCEPTED_VALUES_KEY])
        if self.amLeader is True and self.numPledges >= self.config[cs.F_KEY]:
            if self.confirmedLeader is True:
                return
            self.confirmedLeader = True
            previousAccepts = {}
            for pledge in self.pledgeAccepts:
                for seqno, message in pledge.items():
                    if seqno not in previousAccepts:
                        previousAccepts[int(seqno)] = message
            if len(previousAccepts.keys()) == 0:
                return
            startSeqNo = min(list(previousAccepts.keys()))
            endSeqNo = max(list(previousAccepts.keys()))
            for seq in range(startSeqNo, endSeqNo + 1):
                if seq not in previousAccepts:
                    # There was a skipped slot, send a message to get rid of it
                    message = {}
                    message[cs.MESSAGE_TYPE_KEY] = cs.REPLICA_IGNORE_SLOT
                    message[cs.REPLICA_IGNORE_SLOT_KEY] = seq
                    self.broadcastReplicas(message)
                else:
                    # Add it to the local accept log
                    self.sequenceNum = max(self.sequenceNum, seq)
                    if seq not in self.acceptLog:
                        self.acceptLog[seq] = {'MESSAGE': previousAccepts[seq],
                                                'COUNT': 1}
                    # Send the command to do the message to the replicas again
                    message = {}
                    message[cs.MESSAGE_TYPE_KEY] = cs.REPLICA_COMMAND
                    message[cs.REPLICA_VIEW_KEY] = self.viewNum
                    message[cs.REPLICA_SEQNO_KEY] = self.sequenceNum
                    message[cs.REPLICA_MESSAGE_KEY] = previousAccepts[seq]['MESSAGE']
                    self.broadcastReplicas(message)


    def processNewLeader(self):
        # Update the internal view status
        self.viewNum = self.currentMessage[cs.REPLICA_VIEW_KEY]
        self.amLeader = ((self.viewNum % self.config[cs.NUM_REPLICAS_KEY]) == 0)
        self.amLeader = False
        self.confirmedLeader = False
        self.numPledges = 0
        # Send a pledge message to the new leader
        message = {}
        message[cs.MESSAGE_TYPE_KEY] = cs.REPLICA_YOU_ARE_LEADER
        message[cs.REPLICA_ACCEPTED_VALUES_KEY] = self.acceptLog
        messageBin = json.dumps(message).encode()
        if random.random() >= self.config[cs.LOSS_RATE_KEY]:
            newSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            newSock.connect((self.config[cs.REPLICA_HOSTS_KEY][(self.viewNum % self.config[cs.NUM_REPLICAS_KEY])],
                             self.config[cs.REPLICA_PORTS_KEY][(self.viewNum % self.config[cs.NUM_REPLICAS_KEY])]))
            newSock.send(messageBin)
            newSock.close()


    def processReplicaCommand(self):
        # Update internal data from client command
        commandSeqNum = self.currentMessage[cs.REPLICA_SEQNO_KEY]
        if commandSeqNum in self.committedSeqs:
            message = self.currentMessage
            message[cs.MESSAGE_TYPE_KEY] = cs.REPLICA_ACCEPT
            self.broadcastReplicas(message)
            return
        if commandSeqNum not in self.acceptLog:
            self.acceptLog[commandSeqNum] = {'MESSAGE': self.currentMessage[cs.REPLICA_MESSAGE_KEY],
                                             'COUNT': 1}
        else:
            self.acceptLog[commandSeqNum]['COUNT'] += 1
        self.sequenceNum = max(self.sequenceNum, commandSeqNum)
        # Send replica accept to everybody else with a modified message
        message = self.currentMessage
        message[cs.MESSAGE_TYPE_KEY] = cs.REPLICA_ACCEPT
        self.broadcastReplicas(message)


    def processIgnoreSlot(self):
        seqNo = self.currentMessage[cs.REPLICA_IGNORE_SLOT_KEY]
        self.acceptLog[seqNo] = {'MESSAGE': '\n',
                                 'COUNT': self.config[cs.F_KEY] + 1}


    def processReplicaAccept(self):
        # Update internal data from the new accept message
        commandSeqNum = self.currentMessage[cs.REPLICA_SEQNO_KEY]
        if commandSeqNum in self.committedSeqs:
            return
        if commandSeqNum not in self.acceptLog:
            self.acceptLog[commandSeqNum] = {'MESSAGE': self.currentMessage[cs.REPLICA_MESSAGE_KEY],
                                             'COUNT': 1}
        else:
            self.acceptLog[commandSeqNum]['COUNT'] += 1
        # Check the current sequence of accepted message to see if there are any to commit
        checkCommit = self.nextCommit
        while True:
            if checkCommit in self.acceptLog and self.acceptLog[checkCommit]['COUNT'] >= self.config[cs.F_KEY] + 1:
                # Commit to the chat log
                message = '{} {} {}\n'.format(self.acceptLog[checkCommit]['MESSAGE'][cs.CLIENT_ID_KEY],
                                              self.acceptLog[checkCommit]['MESSAGE'][cs.CLIENT_SEQNO_KEY],
                                              self.acceptLog[checkCommit]['MESSAGE'][cs.CLIENT_CONTENT_KEY])
                # Write the chat to the log file
                self.committedSeqs.add(checkCommit)
                with open(self.logFilename, 'a') as fd:
                    fd.write(message)
                # If leader, send confirmation to the original client!
                if self.confirmedLeader is True:
                    print('LEADER {} CONFIRMED MESSAGE {}'.format(self.replicaID, checkCommit))
                    message = {}
                    message[cs.MESSAGE_TYPE_KEY] = cs.REPLICA_REQUEST_PROCESSED
                    messageBin = json.dumps(message).encode()
                    newSock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    newSock.connect((self.config[cs.CLIENT_HOSTS_KEY][self.currentMessage[cs.REPLICA_MESSAGE_KEY][cs.CLIENT_ID_KEY]],
                                     self.config[cs.CLIENT_PORTS_KEY][self.currentMessage[cs.REPLICA_MESSAGE_KEY][cs.CLIENT_ID_KEY]]))
                    newSock.send(messageBin)
                    newSock.close()
                del self.acceptLog[checkCommit]
                self.nextCommit += 1
                checkCommit += 1
            else:
                # Nothing else is ready to be committed yet
                break
