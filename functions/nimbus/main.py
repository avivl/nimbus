"""Main file for Numbus."""
import commands

# Enter the base-64 encoded, encrypted Slack command token (CiphertextBlob)

COMMANDS = {'help': 'commands.Help',
            'route53': 'commands.Route53',
            'ec2': 'commands.EC2',
            'droplets': 'commands.Droplets',
            'sl': 'commands.SL'}


def handle(event, context):
    """Entry point for lambda."""
    param_map = _formparams_to_dict(event['formparams'])
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
