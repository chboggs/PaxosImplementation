import json
import multiprocessing
import time
from client import Client
from replica import Replica
import consts as cs


class Controller:
    def __init__(self, configFile):
        with open(configFile, 'r') as fd:
            self.config = json.load(fd)
        self.clientProcs = []
        self.replicaProcs = []
        for i in range(self.config[cs.NUM_CLIENTS_KEY]):
            self.clientProcs.append(Client(i, configFile))
        for i in range(self.config[cs.NUM_REPLICAS_KEY]):
            self.replicaProcs.append(Replica(i, configFile))


    def startReplicas(self):
        for proc in self.replicaProcs:
            proc.start()
        time.sleep(1)


    def startClients(self):
        for proc in self.clientProcs:
            proc.start()


    def terminateReplica(self, index):
        self.replicaProcs[index].terminate()


    def terminateAll(self):
        for proc in self.clientProcs:
            proc.terminate()
        for proc in self.replicaProcs:
            proc.terminate()
