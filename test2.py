import time
from controller import Controller


control = Controller('configs/config0.json')
control.startReplicas()
control.startClients()
time.sleep(2)
print('KILLING PRIMARY')
control.terminateReplica(0)
time.sleep(40)
control.terminateAll()
