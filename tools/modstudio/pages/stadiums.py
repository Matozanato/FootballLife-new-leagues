"""Stadiums: stadium-server's home stadiums, competition stadiums and finals"""
from .content import ServerPage


class Stadiums(ServerPage):
    title = "Stadiums"
    hint = "Where each club plays at home, and where the cups and finals are played."
    server = "stadiums"
