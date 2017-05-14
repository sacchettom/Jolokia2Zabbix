"""
Requires:

PyYaml
SimpleJSON
pyjolokia
py-zabbix
"""

import yaml
import simplejson as json
from pyjolokia import Jolokia
from pyzabbix import ZabbixMetric, ZabbixSender
import platform
import time


##
# Loads and parses the configuration
##

class Configuration(object):
    stored_configuration = None

    def __init__(self, configfile=None):
        """

        :rtype: Configuration
        """
        if configfile is not None:
            self.configuration = configfile

    # Loads the configuration from a yaml file
    def load_configuration(self, configfile):
        try:
            config_file = open(configfile, 'r')
            self.stored_configuration = yaml.load(config_file.read())
            config_file.close()
        except Exception as e:
            print('Sorry, couldn\'t find or open the configuration file %s\n' % configfile)
            raise e

    @property
    def keys(self):
        """List of keys defined in the configuration file (excludes the key 'common'"""
        keys = []
        for item in self.stored_configuration:
            if item['key'] != 'common':
                keys.append(item['key'])
        return keys

    @property
    def keys_json(self):
        """ Returns a zabbix-compatible json list of configured keys"""
        data = []
        for item in self.configuration:
            data.append({'{#KEY}': item['key']})
        return json.dumps(data)

    def jolokia_requests(self, key):
        """Returns a Jolokia item with all the requests for a given java instance key
        Parameters:
        key: the key of the jvm as in the configuration file"""
        requests_list = []
        polls = None
        for item in self.configuration:
            if item['key'] == key:
                polls = Jolokia(item['endpoint'])
                # Adds endpoint-specific requests
                try:
                    requests_list.extend(item['requests'])
                except KeyError:
                    pass
            # Adds common requests
            if item['key'] == 'common':
                try:
                    requests_list.extend(item['requests'])
                except KeyError:
                    pass
        if polls is not None:
            for request in requests_list:
                polls.add_request(type='read', mbean=request['mbean'], attribute=request['attribute'],
                                  path=request['path'])

        return polls

    def poll_frequency(self, key):
        """Returns the requested poll frequency in seconds for the specified endpoint's key"""
        try:
            value = (self.configuration_for_key(key)['poll-frequency'])
        except KeyError:
            try:
                value = (self.common_configuration()['poll-frequency'])
            except KeyError:
                return None
        return value

    @property
    def configuration(self):
        return self.stored_configuration

    @configuration.setter
    def configuration(self, configfile):
        self.load_configuration(configfile)

    def configuration_for_key(self, key):
        for item in self.configuration:
            if item['key'] == key:
                return item
        return None

    def common_configuration(self):
        return self.configuration_for_key('common')


class ConversionFactory(object):
    configuration = None
    hostname = None

    def __init__(self, configuration_file):

        self.configuration = Configuration(configuration_file)
        self.hostname = platform.node()

    def mbean_name_reformatter(self, mbean_name):
        finalstring = ''
        for character in mbean_name:
            if character == '.' or character == ',' or character == '.' or character == '=' or character == '/' or character == '\\':
                finalstring = "%s%c" % (finalstring, '_')
            else:
                finalstring = "%s%c" % (finalstring, character)
        return finalstring

    def poll(self, key):
        """Polls the Jolokia endpoint and returns the results in a dictionary
        TODO: This should be integrated with zabbix_data_maker, there's no
        point in doing 2 subsequent data transformations"""
        final_results = []
        results = self.configuration.jolokia_requests(key).getRequests()
        for result in results:
            request = result['request']
            output_key = "%s.%s.%s.%s" % (
                key, self.mbean_name_reformatter(request['mbean']), request['attribute'], request['path'])
            if result['status'] == 200:
                final_results.append({'key': output_key, 'value': result['value']})
            else:
                final_results.append({'key': output_key, 'value': 'Err'})
        print final_results
        return final_results

    def zabbix_data_maker(self, key):
        """Polls an endpoint and returns the data as an array of ZabbixMetric objects"""
        zabbix_data = []
        results = self.poll(key)
        for result in results:
            zabbix_data.append(ZabbixMetric(self.hostname, result['key'], result['value']))
        zabbix_data.append(ZabbixMetric(self.hostname, 'jolokia.keys', self.configuration.keys_json))
        return zabbix_data

    def send_zabbix_data(self, key):
        """Polls one endpoint and sends to Zabbix the data"""
        ZabbixSender(use_config=True).send(self.zabbix_data_maker(key))

    @property
    def poll_intervals(self):
        """Returns a dictionary with the all requested poll intervals"""
        intervals = []
        for key in self.configuration.keys:
            intervals.append((key, self.configuration.poll_frequency(key)))
        return intervals

    def start(self):
        intervals = self.poll_intervals
        while True:
            current_time = int(time.time())
            for (key, poll_frequency) in intervals:
                if (current_time % poll_frequency) == 0:
                    self.send_zabbix_data(key)
            time.sleep(1)


if __name__ == '__main__':

    cfactory = ConversionFactory('config.yaml')
    cfactory.start()
    exit(0)
