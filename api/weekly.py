# -*- coding: utf-8 -*-
"""Weekly da Sprint — cron de segunda às 18h (Fortaleza), rito da Sprint.
Mesma lógica de api/daily.py; só muda o e-mail montado (MODO = "weekly")."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from daily import handler as _Base  # noqa: E402


class handler(_Base):
    MODO = "weekly"
