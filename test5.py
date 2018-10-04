import time
from controller import Controller


control = Controller('configs/config5.json')
control.startReplicas()
control.startClients()
time.sleep(15)
control.terminateAll()
