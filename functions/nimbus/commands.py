"""Commands classes."""
from base64 import b64decode
import boto3
import digitalocean
from slacker import Slacker
import SoftLayer
import re
import urllib2


class AbstractCommand(object):
    """Base class for commands."""

    def __init__(self, args):
        """Get configuration data from DynamoDB."""
        client = boto3.client('dynamodb')
        config = client.scan(TableName='nimbus')['Items'][0]
        kms = boto3.client('kms')
        # Slack will send us a token with each request, we need to validate is
        # in order to make sure that the code is callled from our "own" slack.
        if 'SlackExpected' in config:
            encrypted_expected_token = config['SlackExpected']['S']
            expected_token = kms.decrypt(CiphertextBlob=b64decode(
                encrypted_expected_token))['Plaintext']
            if args['token'] != expected_token:
                print "No matching token found!"
                return
        else:
            print "Encrypted excpcted token not found in DB"
            return

        # Slack API token.
        if 'SlackAPI' in config:
            encrypted_slack_token = config['SlackAPI']['S']
            self.slack_token = kms.decrypt(CiphertextBlob=b64decode(
                encrypted_slack_token))['Plaintext']
        else:
            print "Slack API token not found"
            return

        # DigitalOcean API token.
        if 'DigitalOcean' in config:
            encrypted_digitalocean_token = config['DigitalOcean']['S']
            self.digitalocean_token = kms.decrypt(CiphertextBlob=b64decode(
                encrypted_digitalocean_token))['Plaintext']
        else:
            self.digitalocean_token = ""

        # Softlayern username.
        if 'SLUserName' in config:
            encrypted_softalyer_username = config['SLUserName']['S']
            self.softalyer_username = kms.decrypt(CiphertextBlob=b64decode(
                encrypted_softalyer_username))['Plaintext']
        else:
            self.softalyer_username = ""

        # Softlayern API key.
        if 'SLAPI' in config:
            encrypted_softalyer_api_key = config['SLAPI']['S']
            self.softalyer_api_key = kms.decrypt(CiphertextBlob=b64decode(
                encrypted_softalyer_api_key))['Plaintext']
        else:
            self.softalyer_api_key = ""

        # Bot icon URL
        if 'icon' in config:
            self.icon = config['icon']['S']
        else:
            self.icon = ""

        # Name of the bot as displayed by Slack
        if 'BotName' in config:
            self.botname = config['BotName']['S']
        else:
            self.botname = 'Nimbus'

        self.channel_name = args['channel_name'].split('+')[0]
        self.user_name = args['user_name'].split('+')[0]
        self.args = args['text'].split('+')[2]
        self.slack = Slacker(self.slack_token)

    def run(self):
        """Base function for commands excecution."""
        return

    def post_message(self, msg, attachments):
        """Send a formated message to Slack."""
        self.slack.chat.post_message(
            '#' + self.channel_name,
            msg,
            username=self.botname,
            as_user=False,
            attachments=attachments,
            icon_url=self.icon)


class Route53(AbstractCommand):

    """Serach for dns records at Route53."""

    def run(self):
        """Entry point fo rthe serach. Iterate over dns records."""
        client = boto3.client('route53')
        hosted_zones = client.list_hosted_zones()['HostedZones']
        dns = urllib2.unquote(self.args)
        if dns.find('|') >= 0:
            # Slack will send in the following format http://xxx.yyy.zz
            #  |xxx.yyy.zz>"""
            dns = (urllib2.unquote(self.args)).split('|')[1].rstrip('>')
        results = []
        for hosted_zone in hosted_zones:
            record_sets = client.list_resource_record_sets(
                HostedZoneId=hosted_zone['Id'])['ResourceRecordSets']
            for record_set in record_sets:
                if record_set.get('Name').rstrip('.') == dns:
                    if record_set['Type'] == 'CNAME' or record_set[
                            'Type'] == 'A':
                        if 'ResourceRecords' not in record_set:
                            print('ResourceRecords not found in %s'
                                  % record_set)
                            continue
                        for value in [x['Value']
                                      for x
                                      in record_set['ResourceRecords']]:
                            results.append({
                                'Type': record_set['Type'],
                                'TTL': record_set['TTL'],
                                'Value': value
                                })
        attachments = [{'title': dns,
                        'color': 'good',
                        'fields': [{'title': field,
                                    'value': value,
                                    'short': True}
                                   for field, value in record.items()]}
                       for record in results]
        if len(results) == 0:
            attachments = [{
                'color': 'danger',
                'title': 'Not found',
                'text': dns
            }]
        self.post_message('Route53 Search', attachments)


class EC2(AbstractCommand):

    """Search for ec2 instances at AWS."""

    def run(self):
        """Entry point for the search. Iterate over instances records."""
        ec2c = boto3.client('ec2')
        search = urllib2.unquote(self.args)
        regions = ec2c.describe_regions()['Regions']
        results = []
        attachments = []
        for region in regions:
            ec2 = boto3.resource('ec2', region_name=region['RegionName'])
            instances = ec2.instances.filter(
                Filters=[{'Name': 'instance-state-name',
                          'Values': ['running']},
                         {'Name': 'tag:Name', 'Values': [search]}])
            for instance in instances:
                for tag in instance.tags:
                    if tag['Key'] == 'Name':
                        results.append({
                            'Name': tag['Value'],
                            'Type': instance.instance_type,
                            'VPC': instance.vpc_id,
                            'Region': region['RegionName']
                            })
                    attachments = [{'color': 'good',
                                    'fields': [{'title': field, 'value': value,
                                                'short': True}
                                               for field, value in
                                               record.items()]}
                                   for record in results]
        if attachments == []:
            attachments = [{
                'color': 'danger',
                'title': 'Not found',
                'text': search
            }]
        self.post_message('EC2 Search for ' + search, attachments)


class Droplets(AbstractCommand):

    """Search for droplet at DigitalOcean."""

    def run(self):
        """Entry point for the search. Iterate over instances records."""
        if len(self.digitalocean_token) == 0:
            attachments = [{
                'color': 'danger',
                'title': 'DO Token not found',
            }]
            self.post_message('Droplets Search', attachments)
            return
        search = urllib2.unquote(self.args)
        manager = digitalocean.Manager(token=self.digitalocean_token)
        my_droplets = manager.get_all_droplets()
        results = []
        attachments = []
        for droplet in my_droplets:
            m = re.search(search, droplet.name)
            if m:
                results.append({
                    'Name': droplet.name,
                    'Region': droplet.region['name']
                    })
                attachments = [{'color': 'good',
                                'fields': [{'title': field, 'value': value,
                                            'short': True}
                                           for field, value in
                                           record.items()]}
                               for record in results]
        if attachments == []:
            attachments = [{
                'color': 'danger',
                'title': 'Not found',
                'text': search
            }]
        self.post_message('Droplets Search', attachments)


class SL(AbstractCommand):

    """Search for VM's at Softlayer."""

    def run(self):
        """Entry point for the search. Iterate over VM's records."""
        if len(self.softalyer_username) == 0:
            attachments = [{
                'color': 'danger',
                'title': 'SL Username not found',
            }]
            self.post_message('SL Search', attachments)
            return
        if len(self.softalyer_api_key) == 0:
            attachments = [{
                'color': 'danger',
                'title': 'SL API Key not found',
            }]
            self.post_message('SL Search', attachments)
            return
        search = urllib2.unquote(self.args)
        client = SoftLayer.create_client_from_env(
            username=self.softalyer_username,
            api_key=self.softalyer_api_key)
        mgr = SoftLayer.VSManager(client)
        vsi = mgr.list_instances()
        results = []
        attachments = []
        for vs in vsi:
            m = re.search(search, vs['hostname'])
            if m:
                results.append({
                    'Name': vs['hostname'],
                    'Data Center': vs['datacenter']['longName']
                })
                attachments = [{'color': 'good',
                                'fields': [{'title': field, 'value': value,
                                            'short': True}
                                           for field, value in
                                           record.items()]}
                               for record in results]
        if attachments == []:
            attachments = [{
                'color': 'danger',
                'title': 'Not found',
                'text': search
            }]
        self.post_message('SL Search', attachments)
