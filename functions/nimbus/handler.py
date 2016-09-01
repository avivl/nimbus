import commands
from config import Config, ConfigError
from message_poster import MessagePoster


COMMANDS = {'help': commands.Help,
            'route53': commands.Route53Search,
            'ec2': commands.EC2Search,
            'droplets': commands.DODropletsSearch,
            'sl': commands.SoftLayerSearch}


def is_valid_slack_secret(config, secret):
    """
    Slack will send us a token with each request, we need to validate is
    in order to make sure that the code is callled from our "own" slack.
    """
    return config.DEBUG or secret == config.decrypt('SlackExpected')


class NoResultsError(Exception):
    pass


def run_command(command_name, secret_token, channel_name, user_name, text):
    """run the command."""
    # init config
    config = Config()

    # check slack secret
    if not is_valid_slack_secret(config, secret_token):
        print 'slack secret does not match'
        return

    # init message poster for responding on slack
    try:
        message_poster = MessagePoster(config, channel_name, user_name)
    except ConfigError as e:
        print 'error initializing', e
        return

    # init and run command
    command_class = COMMANDS.get(command_name, COMMANDS['help'])
    title = '%s: %s' % (command_class.name(), text)
    try:
        command = command_class(config)
        results = command.run(text)
        if not results:
            raise NoResultsError(text)
        message_poster.post_results(title, results)
    except ConfigError as e:
        message_poster.post_error(title, 'Configuration Error', str(e))
    except NoResultsError as e:
        message_poster.post_error(title, 'No Results', str(e))
    except Exception as e:
        message_poster.post_error(title, 'Unexpected Error', str(e))
