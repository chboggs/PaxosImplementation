# Paxos Implementation
## Christopher Boggs and Tiberiu Vilcu
## 26 February 2018

This project is written in and uses Python3.
The RandomWords package must also be installed. 'pip install RandomWords'


Process configuration file

Both client and replica processes read in a configuration file that contains runtime parameters including information about the number of processes and their hosts and ports. The file is in JSON format.
The file can be made manually or by using the 'createconfig.py' script. All parameters can be changed in the script, then it can be run with 'python createconfig.py filename.json' to generate the JSON config file.
An example config file can be found at 'configs/config0.json'


Running a client process individually

A config file is needed for the process, and the client process number must be known (and not used for any other client).
To start a process, use the runclient.py script like 'python runclient.py clientID config.json'


Running a replica process individually

A config file is needed for the process, and the replica process number must be known (and not used for any other replica).
Replica number 0 should be created or start running last.
To start a process, use the runreplica.py script like 'python runreplica.py replicaID config.json'


Running a test case

Test cases are created to simulate certain scenarios (as described in the project specs). These will use the pre-generated config files and will locally create all client/replica processes and run the simulation for a set amount of time before finishing.
They can be run with 'python test.py'


Comparing chat logs

All replica logs are written to in the logs/ directory. They can be diffed to compare if they are prefixes of another to show they're correct.
