import time
from controller import Controller


control = Controller('configs/config1.json')
control.startReplicas()
control.startClients()
time.sleep(15)
control.terminateAll()
