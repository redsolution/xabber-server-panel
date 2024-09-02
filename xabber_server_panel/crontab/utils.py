from xabber_server_panel.crontab.models import CronJob

from django.conf import settings

import subprocess
import json


"""
    Write crontab functions here
    
    example:
        def test_crontab_func(*args, **kwargs):
            youre func logic
"""


def run_terminal_function(command, *args):
    result = subprocess.run(
        [command, *args],
        shell=True, check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )