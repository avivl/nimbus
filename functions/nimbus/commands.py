"""Commands classes."""
import re

import SoftLayer
import boto3
import digitalocean


class AbstractCommand(object):
    """Base class for commands."""

    def __init__(self, config):
        """derived can implement to inject configuration."""
        pass

    @classmethod
    def name(cls):
        raise NotImplementedError()

    def run(self, search):
        """Base function for commands excecution."""
        raise NotImplementedError()


class Route53Search(AbstractCommand):

    """Search for dns records on Route53.

    >>> route53 <fqdn>
    """

    @classmethod
    def name(cls):
        return 'AWS Route53 Search'

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


class EC2Search(AbstractCommand):

    """Search for EC2 instances on AWS.

    >>> ec2 <search>
    """

    @classmethod
    def name(cls):
        return 'AWS EC2 Search'

    def run(self, search):
        """Entry point for the search. Iterate over instances records."""
        from multiprocessing.pool import ThreadPool
        ec2c = boto3.client('ec2')
        regions = ec2c.describe_regions()['Regions']

        instance_filters = [{'Name': 'instance-state-name', 'Values': ['running']},
                            {'Name': 'tag:Name', 'Values': [search]}]

        def get_instances(region):
            ec2 = boto3.resource('ec2', region_name=region['RegionName'])
            return ec2.instances.filter(Filters=instance_filters)

        pool = ThreadPool(processes=15)
        async_results = [pool.apply_async(get_instances, (region, ))
                         for region in regions]

        results = []
        for region, async_result in zip(regions, async_results):
            instances = async_result.get()
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


class DODropletsSearch(AbstractCommand):

    """Search for droplet on DigitalOcean.

    >>> droplets <search>
    """

    @classmethod
    def name(cls):
        return 'DO Droplets Search'

    def __init__(self, config):
        super(DODropletsSearch, self).__init__(config)
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


class SoftLayerSearch(AbstractCommand):

    """Search for VM's on Softlayer.

    >>> sl <search>
    """

    @classmethod
    def name(cls):
        return 'SoftLayer Search'

    def __init__(self, config):
        super(SoftLayerSearch, self).__init__(config)
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
    """Help on all commands."""

    @classmethod
    def name(cls):
        return 'help'

    def run(self, args):
        return [{'Name': cls.__name__, 'Help': cls.__doc__}
                for cls in [EC2Search, SoftLayerSearch, Route53Search, DODropletsSearch]]
