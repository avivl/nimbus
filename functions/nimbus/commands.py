"""Commands classes."""
import re

import SoftLayer
import boto3
import digitalocean


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
