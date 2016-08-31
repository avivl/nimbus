"""Main file for Nimbus."""
from handler import run_command


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

    return run_command(command_name, secret_token, channel_name, user_name, text)


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
