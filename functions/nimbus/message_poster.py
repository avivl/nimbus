from slacker import Slacker


class MessagePoster(object):
    """class for posting messages back to the user/ room."""

    def __init__(self, config, channel_name, user_name):
        self.slacker = Slacker(config.decrypt('SlackAPI'))

        self.channel_name = channel_name
        self.user_name = user_name
        self.icon = config.get('icon', '')  # Bot icon URL
        self.botname = config.get('BotName', 'Nimbus')

        self.DEBUG = config.DEBUG

    def post_error(self, msg, title, description):
        self._post(msg, [{
            'color': 'danger',
            'title': title,
            'text': description,
        }])

    def post_results(self, msg, results):
        attachments = [{'color': 'good',
                        'fields': [{'title': field,
                                    'value': value,
                                    'short': True}
                                   for field, value in
                                   record.items()]}
                       for record in results]
        return self._post(msg, attachments)

    def _post(self, msg, attachments):
        """Send a formated message to Slack."""
        if self.DEBUG:
            print dict(
                channel_name='#' + self.channel_name,
                msg=msg,
                username=self.botname,
                as_user=False,
                attachments=attachments,
                icon_url=self.icon)
            return

        self.slacker.chat.post_message(
            '#' + self.channel_name,
            msg,
            username=self.botname,
            as_user=False,
            attachments=attachments,
            icon_url=self.icon)
