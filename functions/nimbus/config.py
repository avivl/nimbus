from base64 import b64decode
import os

import boto3


class ConfigError(Exception):
    pass


class Config(object):
    def __init__(self):
        dynamodb = boto3.client('dynamodb')
        self.config = dynamodb.scan(TableName='nimbus')['Items'][0]
        self.kms = boto3.client('kms')

        # don't authenticate + print to screen
        self.DEBUG = os.getenv('NIMBUS_DEBUG', 'false').lower() == 'true'

    def __getitem__(self, key):
        try:
            return self.config[key].values()[0]
        except KeyError:
            raise ConfigError('missing configuration key %s' % key)

    def __contains__(self, key):
        return key in self.config

    def decrypt(self, key):
        return self.decryptvalue(self[key])

    def decryptvalue(self, value):
        return self.kms.decrypt(CiphertextBlob=b64decode(value))['Plaintext']

    def get(self, key, default=None):
        if key in self:
            return self[key]
        return default
