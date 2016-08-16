"""Main file for Numbus."""
from base64 import b64decode
import boto3
import commands

# Enter the base-64 encoded, encrypted Slack command token (CiphertextBlob)

***REMOVED*** = "***REMOVED***"
kms = boto3.client('kms')
expected_token = kms.decrypt(CiphertextBlob=b64decode(
    ***REMOVED***))['Plaintext']
COMMANDS = {'help': 'commands.Help',
            'route53': 'commands.Route53', 'ec2': 'commands.EC2', 'droplets': 'commands.Droplets'}


def handle(event, context):
    """Entry point for lambda."""
    param_map = _formparams_to_dict(event['formparams'])
    """Check that the caller is legit"""

    if param_map['token'] != expected_token:
        return event
    if len(param_map['text'].split('+')) < 3:
        # call help
        return event
    return handle_command(param_map['text'].split('+')[1],
                          param_map)

""" Get the command and execute it """


def handle_command(commnad_name, text):
    """Call the relevant command."""
    command = COMMANDS.get(commnad_name, COMMANDS['help'])
    command = command + "(" + "text" + ")"
    my_cls = eval(command)
    method = getattr(my_cls, "run")
    return method()


def _formparams_to_dict(s1):
    # Converts the incoming formparams from Slack into a dictionary
    retval = {}
    for val in s1.split('&'):
        k, v = val.split('=')
        retval[k] = v
    return retval
