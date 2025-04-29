# dump_script.py

import os
import django
import io
from django.core.management import call_command

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'safetaxi.settings')  # adjust if your settings module is different
django.setup()

with io.open('data.json', 'w', encoding='utf-8') as f:
    call_command('dumpdata', indent=2, stdout=f)
