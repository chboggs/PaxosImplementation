import sys
from client import Client

client = Client(sys.argv[1], sys.argv[2])
client.start()
