"""Main file for Numbus."""
import commands

# Enter the base-64 encoded, encrypted Slack command token (CiphertextBlob)

COMMANDS = {'help': commands.Help,
            'route53': commands.Route53,
            'ec2': commands.EC2,
            'droplets': commands.Droplets,
            'sl': commands.SL}


def handle(event, context):
    """Entry point for lambda.

    parse slack command and run one of the commands available.
    """
    token, channel_name, user_name, text = _parse_slack_input(event['formparams'])
    # text should be:
    # "nimbus <command> <args>"
    if text.split() < 3:
        # call help
        return event

    _, text = _pop_token(text)  # bot name
    command_name, text = _pop_token(text)

    CommandClass = COMMANDS.get(command_name, COMMANDS['help'])
    command = CommandClass(token, channel_name, user_name)
    return command.run(text)


def _parse_slack_input(query_string):
    """return the slack parameters from a query string."""
    import urlparse
    params = dict(urlparse.parse_qsl(query_string))
    text = params['text']
    text = ' '.join(text.split())  # remove duplicate spaces
    return params['token'], params['channel_name'], params['user_name'], text


def _pop_token(text):
    """return a tuple of the first token and the rest of the string."""
    return text.split(' ', 1)
