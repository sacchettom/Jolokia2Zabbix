import yaml
import simplejson as json
from pyjolokia import Jolokia
from pyzabbix import ZabbixMetric, ZabbixSender
import platform

##
# Loads and parses the configuration
##

class Configuration(object):

    stored_configuration = None

    def __init__(self, configfile=None):
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
        keys = []
        for item in self.stored_configuration:
            if item['key'] != 'common':
                keys.append(item['key'])
        return keys

    # Returns a zabbix-compatible json list of configured keys
    @property
    def keys_json(self):
        data = []
        for item in self.configuration:
            data.append({'{#KEY}':item['key']})
        return json.dumps(data)

    def jolokia_requests(self, key):
        requests_list = []
        for item in  self.configuration:
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
        for request in requests_list:
            polls.add_request(type='read', mbean=request['mbean'], attribute=request['attribute'], path=request['path'])

        return polls


    @property
    def configuration(self):
        return self.stored_configuration

    @configuration.setter
    def configuration(self, configfile):
        self.load_configuration(configfile)


class ConversionFactory(object):

    configuration = None
    hostname = None

    def __init__(self, configuration_file):
        """

        :type configuration: Configuration
        """
        self.configuration = Configuration(configuration_file)
        self.hostname = platform.node()

    def mbean_name_reformatter(self,mbean_name):
        finalstring = ''
        for character in mbean_name:
            if character == '.' or character == ',' or character == '.' or character == '=' or character == '/' or character == '\\' :
                finalstring = "%s%c" % (finalstring, '_')
            else:
                finalstring = "%s%c" % (finalstring, character)
        return finalstring

    def poll(self):
        final_results = []
        for key in self.configuration.keys:
            results = self.configuration.jolokia_requests(key).getRequests()
            for result in results:
                request = result['request']
                output_key = "%s.%s.%s.%s" % (key, self.mbean_name_reformatter(request['mbean']), request['attribute'], request['path'])
                if result['status'] == 200:
                    final_results.append({'key': output_key, 'value' : result['value']})
                else:
                    final_results.append({'key': output_key, 'value' : 'Err'})
        return final_results

    def zabbix_data_maker(self):
        zabbix_data = []
        results = self.poll()
        for result in results:
            zabbix_data.append(ZabbixMetric(self.hostname, result['key'], result['value']))
        zabbix_data.append(ZabbixMetric(self.hostname, 'jolokia.keys', self.configuration.keys_json))
        return zabbix_data

    def send_zabbix_data(self):
        result = ZabbixSender(use_config=True).send(self.zabbix_data_maker())
        print result



if __name__ == '__main__':
    cfactory = ConversionFactory('config.yaml')
    cfactory.send_zabbix_data()


