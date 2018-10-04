import time
from controller import Controller


control = Controller('configs/config4.json')
control.startReplicas()
control.startClients()
time.sleep(10)
control.terminateReplica(0)
time.sleep(20)
control.terminateAll()
