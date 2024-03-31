from django.core.mail import EmailMultiAlternatives
from django.conf import settings

from celery import shared_task
from PIL import Image

@shared_task
def resize_image(image_path, thumbnail_path, size=(100, 100)):
    """
    Распаковывает изображение по указанному пути, изменяет его размер и сохраняет миниатюру.
    """
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size)
            img.save(thumbnail_path)
    except Exception as e:
        print(f"Ошибка при обработке изображения: {e}")

@shared_task
def send_email(user_email, subject, message):
    msg = EmailMultiAlternatives(
        subject,
        message,
        settings.EMAIL_HOST_USER ,
        [user_email]
    )
    msg.send()

@shared_task
def do_import():
    pass


