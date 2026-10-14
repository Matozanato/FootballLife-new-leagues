"""Commentary: commentary-server's language per club and per competition"""
from .content import ServerPage


class Commentary(ServerPage):
    title = "Commentary"
    hint = "Which language the commentary speaks, for each club and each competition."
    server = "commentary"
