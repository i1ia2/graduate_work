from celery import Celery

import os


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'djangoProject.settings')

app = Celery('djangoProject')
app.conf.broker_url ='amqp://guest:guest@localhost'
app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()


def shared_task():
    return "0"