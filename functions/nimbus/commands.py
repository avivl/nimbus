"""Commands classes."""
import re


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
        import boto3
        client = boto3.client('route53')
        hosted_zones = client.list_hosted_zones()['HostedZones']
        if search.find('|') >= 0:
            # Slack will send in the following format http://xxx.yyy.zz
            #  |xxx.yyy.zz>"""
            search = search.split('|')[1].rstrip('>')
        for hosted_zone in hosted_zones:
            record_sets = client.list_resource_record_sets(
                HostedZoneId=hosted_zone['Id'])['ResourceRecordSets']
            for record_set in record_sets:
                if (record_set['Name'].rstrip('.') == search
                        and record_set['Type'] in ['CNAME', 'A']
                        and 'ResourceRecords' in record_set):

                    for rr in record_set['ResourceRecords']:
                        yield {
                            'Type': record_set['Type'],
                            'TTL': record_set['TTL'],
                            'Value': rr['Value']
                        }


class EC2Search(AbstractCommand):

    """Search for EC2 instances on AWS.

    >>> ec2 <search>
    """

    @classmethod
    def name(cls):
        return 'AWS EC2 Search'

    def run(self, search):
        """Entry point for the search. Iterate over instances records."""
        import boto3
        from Queue import Queue
        from threading import Thread

        ec2c = boto3.client('ec2')
        regions = ec2c.describe_regions()['Regions']

        instance_filters = [{'Name': 'instance-state-name',
                             'Values': ['running']},
                            {'Name': 'tag:Name',
                             'Values': [search]}]

        def get_instances(region_name, q):
            ec2 = boto3.resource('ec2', region_name=region_name)
            q.put((region_name, ec2.instances.filter
                   (Filters=instance_filters)))

        q = Queue()
        threads = [
            Thread(
                target=get_instances,
                args=(
                    region['RegionName'],
                    q)).start() for region in regions]
        for _ in range(len(threads)):
            region_name, instances = q.get()
            for instance in instances:
                for tag in instance.tags:
                    if tag['Key'] == 'Name':
                        yield {
                            'Name': tag['Value'],
                            'Type': instance.instance_type,
                            'VPC': instance.vpc_id,
                            'Region': region_name
                        }


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
        import digitalocean

        manager = digitalocean.Manager(token=self.digitalocean_token)
        my_droplets = manager.get_all_droplets()

        for droplet in my_droplets:
            if re.search(search, droplet.name):
                yield {
                    'Name': droplet.name,
                    'Region': droplet.region['name']
                }


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
        import SoftLayer

        client = SoftLayer.create_client_from_env(
            username=self.softalyer_username,
            api_key=self.softalyer_api_key)

        mgr = SoftLayer.VSManager(client)
        vsi = mgr.list_instances()

        for vs in vsi:
            if re.search(search, vs['hostname']):
                yield {
                    'Name': vs['hostname'],
                    'Data Center': vs['datacenter']['longName']
                }


class GCESearch(AbstractCommand):

    """Search for VM's on GCE.

    >>> gce <search>
    """

    @classmethod
    def name(cls):
        return 'GCE Search'

    def __init__(self, config):
        super(GCESearch, self).__init__(config)
        import boto3
        import json
        import os
        import tempfile
        s3 = boto3.client("s3")
        kms = boto3.client('kms')
        self.tmp_dir = tempfile.mkdtemp()
        for key in config['GCETokens']:
            jsondata = config.decryptvalue(key)
            filename = json.loads(jsondata)["project_id"]
            with open(self.tmp_dir + "/" + filename + ".json", 'w') as jfile:
                jfile.write(jsondata)

    def run(self, search):
        """Entry point for the search. Iterate over VM's records."""
        from oauth2client.service_account import ServiceAccountCredentials
        from googleapiclient import discovery
        import glob
        import json
        import shutil
        scopes = ['https://www.googleapis.com/auth/compute.readonly']
        for filename in glob.glob(self.tmp_dir + '/*.json'):
            with open(filename) as data_file:
                data = json.load(data_file)
            project_id = data["project_id"]
            credentials = ServiceAccountCredentials.from_json_keyfile_name(
                filename, scopes=scopes)
            compute = discovery.build('compute', 'v1', credentials=credentials)
            zones = compute.zones()
            request = zones.list(project=project_id)
            filter = 'name eq {}.*'.format(search)
            while request is not None:
                response = request.execute()
                for zone in response['items']:
                    instances = compute.instances().list(
                        project=project_id, zone=zone['name'],
                        filter=filter).execute()
                    for instance in instances.get('items', []):
                        yield {
                            'Name': instance['name'],
                            'Zone': zone['name'],
                            'Project': project_id,
                            'Type': instance['machineType'].rsplit('/', 1)[-1]
                        }
                request = zones.list_next(previous_request=request,
                                          previous_response=response)
        shutil.rmtree(self.tmp_dir)


class Help(AbstractCommand):
    """Help on all commands."""

    @classmethod
    def name(cls):
        return 'help'

    def run(self, args):
        for kls in [
                EC2Search,
                SoftLayerSearch,
                Route53Search,
                DODropletsSearch,
                GCESearch]:
            yield {'Name': kls.__name__, 'Help': kls.__doc__}
