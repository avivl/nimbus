"""Coammnds classes."""
from base64 import b64decode
import boto3
from slacker import Slacker
import urllib2

***REMOVED*** = '***REMOVED***'


class AbstractCommand(object):

    """Base class for commands."""

    def __init__(self, args):
        """Set up."""
        self.channel_name = args['channel_name'].split('+')[0]
        self.user_name = args['user_name'].split('+')[0]
        self.args = args['text'].split('+')[2]
        self.botname = 'Nimbus'
        self.icon = 'http://am.rounds.com/cloudy_robot_200.png'
        kms = boto3.client('kms')
        self.slack_token = kms.decrypt(CiphertextBlob=b64decode(
            ***REMOVED***))['Plaintext']
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
                                'Value': value})
        attachments = [{'title': dns,
                        'color': 'good',
                        'fields': [{'title': field, 'value': value, 'short': True}
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
                            'Region': region['RegionName']})
                    attachments = [{'title': search,
                                    'color': 'good',
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
        self.post_message('EC2 Search', attachments)
