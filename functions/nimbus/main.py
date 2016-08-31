"""Main file for Numbus."""
import commands

# Enter the base-64 encoded, encrypted Slack command secret (CiphertextBlob)

COMMANDS = {'help': commands.Help,
            'route53': commands.Route53,
            'ec2': commands.EC2,
            'droplets': commands.Droplets,
            'sl': commands.SL}


def handle(event, context):
    """Entry point for lambda.

    parse slack command and run one of the commands available.
    """
    secret_token, channel_name, user_name, text = _parse_slack_input(event['formparams'])
    # text should be:
    # "nimbus <command> <args>"
    if text.split() < 3:
        # call help
        return event

    _, text = _pop_token(text)  # bot name
    command_name, text = _pop_token(text)

    CommandClass = COMMANDS.get(command_name, COMMANDS['help'])

    return run_command(CommandClass, secret_token, channel_name, user_name, text)


def run_command(CommandClass, secret_token, channel_name, user_name, text):
    from commands import Config, UserError, ConfigError, MessagePoster, is_valid_slack_secret
    # init config
    config = Config()

    # check slack secret
    if not is_valid_slack_secret(config, secret_token):
        print 'slack secret does not match'
        return

    # init message poster for responding
    try:
        message_poster = MessagePoster(config, channel_name, user_name)
    except ConfigError as e:
        print 'error initializing', e
        return

    # init and run command
    try:
        command = CommandClass(config)
        results = command.run(text)
        if not results:
            raise UserError('Not Found', text)
    except ConfigError as e:
        results = [{
            'color': 'danger',
            'title': str(e),
        }]
    except UserError as e:
        results = [{
            'color': 'danger',
            'title': e.title,
            'text': e.description,
        }]

    # respond with results
    message_poster.post_message(CommandClass.__name__, results)


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
