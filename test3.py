import time
from controller import Controller

F = 3

control = Controller('configs/config1.json')
control.startReplicas()
control.startClients()
time.sleep(5)
for i in range(F):
    control.terminateReplica(i)
    time.sleep(10)
control.terminateAll()
