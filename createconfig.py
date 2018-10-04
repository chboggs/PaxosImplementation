import json
import sys
import consts as cs

config = {}
F = 3
nReplicas = 2 * F + 1
nClients = 1
clientTimeout = 6
livenessWindow = 3
lossRate = 0.0
skipSlot = False
IPbase = 54550
config[cs.F_KEY] = 3
config[cs.NUM_REPLICAS_KEY] = nReplicas
config[cs.NUM_CLIENTS_KEY] = nClients
config[cs.CLIENT_HOSTS_KEY] = ['localhost'] * nClients
config[cs.CLIENT_PORTS_KEY] = [IPbase + i for i in range(nClients)]
config[cs.REPLICA_HOSTS_KEY] = ['localhost'] * nReplicas
config[cs.REPLICA_PORTS_KEY] = [IPbase + nClients + i for i in range(nReplicas)]
config[cs.CLIENT_TIME_KEY] = clientTimeout
config[cs.LIVE_WINDOW_KEY] = livenessWindow
config[cs.LOSS_RATE_KEY] = lossRate
config[cs.SKIP_SLOT_KEY] = skipSlot
with open(sys.argv[1], 'w') as fd:
    json.dump(config, fd)
