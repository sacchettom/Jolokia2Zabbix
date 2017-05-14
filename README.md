## Jolokia2Zabbix

A Jolokia to Zabbix trapper daemon.
Picks the data from Jolokia's rest interface, and sends it to the Zabbix trapper.

### Why:

We know that Zabbix has its nice Java gateway, and can also poll JXM directly.
But I needed to:

1. Support multiple JVMs on the same machine, allowing to create a self-discovery rule for them;
2. Avoid opening extra ports on the hosts;
3. Avoid having the JMX client load custom libraries to interact with the non-default mbeans running on the server
   (in my case, Oracle WebLogic).
   
### How it works:

1. Launches a Unix daemon;
2. The daemon gets its configuration from a YAML file, and from Zabbix agent's configuration file;
3. The daemon will poll Jolokia at the requested intervals and send the data to Zabbix.

Additionally, the daemon will also send to Zabbix a json item (jolokia.keys) to enable a discovery rule of the configured
Jolokia endpoints.

### Credits and Requirements:

This code uses the following libraries:
1. [PyYAML] (http://pyyaml.org/wiki/PyYAML)
2. [SimpleJSON] (https://github.com/simplejson/simplejson)
3. [pyjolokia] (https://github.com/cwood/pyjolokia)
4. [py-zabbix] (https://github.com/blacked/py-zabbix)

All libraries are downloadable with pip.
Developed using Python 2.7, Python3 should woulk fine but has not been tested.