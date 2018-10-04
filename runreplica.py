import sys
from replica import Replica

replica = Replica(sys.argv[1], sys.argv[2])
replica.start()
