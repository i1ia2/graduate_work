# from celery import shared_task
# from django.core.mail import EmailMultiAlternatives
# from django.conf import settings
#
# @shared_task
# def send_email(user_email, subject, message):
#     msg = EmailMultiAlternatives(
#         subject,
#         message,
#         settings.EMAIL_HOST_USER ,
#         [user_email]
#     )
#     msg.send()
#
# @shared_task
# def do_import():
#     pass