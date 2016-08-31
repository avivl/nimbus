"""Commands classes."""
from base64 import b64decode
import os
import re

from slacker import Slacker
import SoftLayer
import boto3
import digitalocean


# don't authenticate + print to screen
DEBUG = os.getenv('NIMBUS_DEBUG', 'true').lower() == 'true'


def is_valid_slack_secret(config, secret):
    """
    Slack will send us a token with each request, we need to validate is
    in order to make sure that the code is callled from our "own" slack.
    """
    return DEBUG or secret == config.decrypt('SlackExpected')


class MessagePoster(object):
    """class for posting messages back to the user/ room."""

    def __init__(self, config, channel_name, user_name):
        self.slacker = Slacker(config.decrypt('SlackAPI'))
        self.channel_name = channel_name
        self.user_name = user_name
        self.icon = config.get('icon', '')  # Bot icon URL
        self.botname = config.get('BotName', 'Nimbus')

    def post_error(self, title, description):
        self._post([{
            'color': 'danger',
            'title': title,
            'text': description,
        }])

    def post_results(self, msg, results):
        attachments = [{'color': 'good',
                        'fields': [{'title': field,
                                    'value': value,
                                    'short': True}
                                   for field, value in
                                   record.items()]}
                       for record in results]
        return self._post(msg, attachments)

    def _post(self, msg, attachments):
        """Send a formated message to Slack."""
        if DEBUG:
            print dict(
                channel_name='#' + self.channel_name,
                msg=msg,
                username=self.botname,
                as_user=False,
                attachments=attachments,
                icon_url=self.icon)
            return

        self.slacker.chat.post_message(
            '#' + self.channel_name,
            msg,
            username=self.botname,
            as_user=False,
            attachments=attachments,
            icon_url=self.icon)


class Config(object):
    def __init__(self):
        client = boto3.client('dynamodb')
        self.config = client.scan(TableName='nimbus')['Items'][0]
        self.kms = boto3.client('kms')

    def __getitem__(self, key):
        try:
            return self.config[key]['S']
        except KeyError:
            raise ConfigError('missing configuration key %s' % key)

    def __contains__(self, key):
        return key in self.config

    def decrypt(self, key):
        return self.kms.decrypt(CiphertextBlob=b64decode(self[key]))['Plaintext']

    def get(self, key, default=None):
        return self.config.get(key, default)


class ConfigError(Exception):
    pass


class NoResultsError(Exception):
    pass


class AbstractCommand(object):
    """Base class for commands."""

    def __init__(self, config):
        """Get configuration data from DynamoDB."""
        self.init_command(config)

    def run(self, search):
        """Base function for commands excecution."""
        pass

    def init_command(self, config):
        """derived can implement to inject configuration."""
        pass


class Route53(AbstractCommand):

    """Serach for dns records at Route53."""

    def run(self, search):
        """Entry point fo rthe serach. Iterate over dns records."""
        client = boto3.client('route53')
        hosted_zones = client.list_hosted_zones()['HostedZones']
        if search.find('|') >= 0:
            # Slack will send in the following format http://xxx.yyy.zz
            #  |xxx.yyy.zz>"""
            search = search.split('|')[1].rstrip('>')
        results = []
        for hosted_zone in hosted_zones:
            record_sets = client.list_resource_record_sets(
                HostedZoneId=hosted_zone['Id'])['ResourceRecordSets']
            for record_set in record_sets:
                if (record_set['Name'].rstrip('.') == search
                        and record_set['Type'] in ['CNAME', 'A']
                        and 'ResourceRecords' in record_set):

                    results += [{
                        'Type': record_set['Type'],
                        'TTL': record_set['TTL'],
                        'Value': rr['Value']
                        } for rr in record_set['ResourceRecords']]

        return results


class EC2(AbstractCommand):

    """Search for ec2 instances at AWS."""

    def run(self, search):
        """Entry point for the search. Iterate over instances records."""
        ec2c = boto3.client('ec2')
        regions = ec2c.describe_regions()['Regions']

        instance_filters = [{'Name': 'instance-state-name', 'Values': ['running']},
                            {'Name': 'tag:Name', 'Values': [search]}]

        results = []
        for region in regions:
            ec2 = boto3.resource('ec2', region_name=region['RegionName'])
            instances = ec2.instances.filter(Filters=instance_filters)
            for instance in instances:
                for tag in instance.tags:
                    if tag['Key'] == 'Name':
                        results.append({
                            'Name': tag['Value'],
                            'Type': instance.instance_type,
                            'VPC': instance.vpc_id,
                            'Region': region['RegionName']
                            })
        return results


class Droplets(AbstractCommand):

    """Search for droplet at DigitalOcean."""

    def init_command(self, config):
        self.digitalocean_token = config.decrypt('DigitalOcean')

    def run(self, search):
        """Entry point for the search. Iterate over instances records."""
        manager = digitalocean.Manager(token=self.digitalocean_token)
        my_droplets = manager.get_all_droplets()

        results = []
        for droplet in my_droplets:
            if re.search(search, droplet.name):
                results.append({
                    'Name': droplet.name,
                    'Region': droplet.region['name']
                    })

        return results


class SL(AbstractCommand):

    """Search for VM's at Softlayer."""

    def init_command(self, config):
        self.softalyer_username = config.decrypt('SLUserName')
        self.softalyer_api_key = config.decrypt('SLAPI')

    def run(self, search):
        """Entry point for the search. Iterate over VM's records."""
        client = SoftLayer.create_client_from_env(
            username=self.softalyer_username,
            api_key=self.softalyer_api_key)

        mgr = SoftLayer.VSManager(client)
        vsi = mgr.list_instances()

        results = []
        for vs in vsi:
            if re.search(search, vs['hostname']):
                results.append({
                    'Name': vs['hostname'],
                    'Data Center': vs['datacenter']['longName']
                })

        return results


class Help(AbstractCommand):
    def run(self):
        return []
