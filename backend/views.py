import logging
from distutils.util import strtobool
from random import random, randint
from tasks import resize_image

from rest_framework.request import Request
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from requests import get
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from ujson import loads as load_json
from yaml import load as load_yaml, Loader
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.contrib.auth import authenticate, login
from rest_framework.throttling import UserRateThrottle
from rest_framework import status, throttling

from backend.forms import ShopForm, ProductSearchForm, CustomUserCreationForm
from backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken, User
from backend.serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, \
    OrderItemSerializer, OrderSerializer, ContactSerializer
from backend.signals import new_user_registered, new_order

def index(request):
    if request.method == 'POST':
        form = ShopForm(request.POST)
        if form.is_valid():
            shop = form.save(commit=False)
    else:
        form = ShopForm()

    return render(request, 'index.html', {'form': form})

def product_html(request):
    form = ProductSearchForm(request.GET)
    products = Product.objects.all()

    if form.is_valid():
        search_query = form.cleaned_data['search_query']
        if search_query:
            products = products.filter(nivel__icontains=search_query)
    else:
        products = ProductSearchForm()

    return render(request, 'product_html.html', {'product': products, 'form': form})

def shops_all(request):
    shops = Shop.objects.all()
    return render(request, 'shop.html', {'shops': shops})


def shops_detail(request, shop_id):
    shop = Shop.objects.get(id=shop_id)
    products = ProductInfo.objects.filter(shop=shop)
    return render(request, 'shop_products.html', {'shop': shop, 'products': products})


def upload_image(request):
    if request.method == 'POST' and request.FILES['image']:
        image = request.FILES['image']
        # Сохраняем изображение на сервере
        image_path = 'C:/Users/Илюха/PycharmProjects/graduate_work/djangoProject/image/Image/' + image.name
        with open(image_path, 'wb+') as destination:
            for chunk in image.chunks():
                destination.write(chunk)
        # Запускаем задачу Celery для обработки изображения
        thumbnail_path = 'C:/Users/Илюха/PycharmProjects/graduate_work/djangoProject/image/Image_mine/' + image.name
        resize_image(image_path, thumbnail_path)
        return render(request, 'success.html')
    return render(request, 'upload.html')


class ExampleView(APIView):
    throttle_classes = [UserRateThrottle]

    def get(self, request, format=None):
        content = {
            'status': 'request was permitted'
        }
        return Response(content)


class RandomRateThrottle(throttling.BaseThrottle):
    def allow_request(self, request, view):
        return random.randint(1, 10) != 1

class RegisterAccount(APIView):

    template_name = 'registration.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('product_html')

    # Регистрация методом POST

    def post(self, request, *args, **kwargs):

        # проверяем обязательные аргументы
        if {'first_name', 'last_name', 'email', 'password', 'company', 'position'}.issubset(request.data):

            # проверяем пароль на сложность
            sad = 'asd'
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                # проверяем данные для уникальности имени пользователя

                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    # сохраняем пользователя
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': user_serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы '
                                                        'first_name, last_name, email, password, company, position'})


class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    """

    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def post(self, request, *args, **kwargs):

        # проверяем обязательные аргументы
        if {'token', 'email'}.issubset(request.data):
            email = request.data['email']
            token_value = request.data['token']

            # Ищем токен в базе данных
            token = ConfirmEmailToken.objects.filter(user__email=email, key=token_value).first()

            if token:
                # Подтверждаем аккаунт
                token.user.is_active = True
                token.user.save()

                # Удаляем токен
                token.delete()

                return JsonResponse({'Status': True, 'Message': 'Аккаунт успешно подтвержден.'})
            else:
                return JsonResponse({'Status': False, 'Errors': 'Неверный токен или адрес электронной почты.'})
        else:
            return JsonResponse({'Status': False, 'Errors': 'Укажите адрес электронной почты и токен.'})


class AccountDetails(APIView):
    """
    Класс для управления данными учетной записи пользователя.

    Методы:
    - get: Получить данные о прошедшем проверку подлинности пользователе.
    - post: Обновить данные учетной записи прошедшего проверку пользователя.

    Атрибуты:
    - None
    """

    # получить данные
    def get(self, request: Request, *args, **kwargs):
        """
               Retrieve the details of the authenticated user.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the details of the authenticated user.
        """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    # Редактирование методом POST
    def post(self, request, *args, **kwargs):
        """
                Update the account details of the authenticated user.

                Args:
                - request (Request): The Django request object.

                Returns:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        # проверяем обязательные аргументы

        if 'password' in request.data:
            errors = {}
            # проверяем пароль на сложность
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                error_array = []
                # noinspection PyTypeChecker
                for item in password_error:
                    error_array.append(item)
                return JsonResponse({'Status': False, 'Errors': {'password': error_array}})
            else:
                request.user.set_password(request.data['password'])

        # проверяем остальные данные
        user_serializer = UserSerializer(request.user, data=request.data, partial=True)
        if user_serializer.is_valid():
            user_serializer.save()
            return JsonResponse({'Status': True})
        else:
            return JsonResponse({'Status': False, 'Errors': user_serializer.errors})


class LoginAccount(APIView):
    """
    Класс для авторизации пользователей
    """

    def post(self, request, *args, **kwargs):

        print("Request Data:", request.data)
        if {'email', 'password'}.issubset(request.data):
            user = authenticate(request, username=request.data['email'], password=request.data['password'])

            if user is not None:
                if user.is_active:
                    token, _ = Token.objects.get_or_create(user=user)

                    return JsonResponse({'Status': True, 'Token': token.key})

            return JsonResponse({'Status': False, 'Errors': 'Не удалось авторизовать'})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})



class CategoryView(ListAPIView):
    """
    Класс для просмотра категорий
    """
    queryset = Category.objects.all()
    serializer_class = CategorySerializer


class ShopView(ListAPIView):
    """
    Класс для просмотра списка магазинов
    """
    queryset = Shop.objects.filter(state=True)
    serializer_class = ShopSerializer


class ProductInfoView(APIView):
    """
        A class for searching products.

        Methods:
        - get: Retrieve the product information based on the specified filters.

        Attributes:
        - None
        """

    def get(self, request: Request, *args, **kwargs):
        """
               Retrieve the product information based on the specified filters.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the product information.
               """
        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id')
        category_id = request.query_params.get('category_id')

        if shop_id:
            query = query & Q(shop_id=shop_id)

        if category_id:
            query = query & Q(product__category_id=category_id)

        # фильтруем и отбрасываем дуликаты
        queryset = ProductInfo.objects.filter(
            query).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()

        serializer = ProductInfoSerializer(queryset, many=True)

        return Response(serializer.data)


class BasketView(APIView):
    """
    Класс для управления корзиной покупок пользователя.

    Методы:
    - get: получить товары из корзины пользователя.
    - post: добавить товар в корзину пользователя.
    - put: обновить количество товара в корзине пользователя.
    - delete: удалить товар из корзины пользователя.

    Attributes:
    - None
    """

    # получить корзину
    def get(self, request, *args, **kwargs):
        """

                Извлеките элементы из корзины пользователя.

                Аргументы:
                - request (Запрос): Объект запроса Django.

                Возвращается:
                - Response: Ответ, содержащий товары из корзины пользователя.
                """

        # if not request.user.is_authenticated:
        #     return JsonResponse({'Status': False, 'Error': 'Не удалось авторизоваться'}, status=403)

        basket = Order.objects.filter(
            user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        if not basket.exists():
            return JsonResponse({'Status': False, 'Error': 'Корзина пуста. Товар еще не добавлен.'})

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    # редактировать корзину
    def post(self, request, *args, **kwargs):
        """
            Добавьте товары в корзину пользователя.

            Аргументы:
            - request (Запрос): Объект запроса Django.

            Возвращается:
            - JsonResponse: ответ, указывающий статус операции и любые ошибки.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Не удалось авторизоваться'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            try:
                # print(items_sting)
                # items_dict = load_json(items_sting)
                items_dict = items_sting
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_created = 0
                for order_item in items_dict:
                    order_item.update({'order': basket.id})
                    serializer = OrderItemSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return JsonResponse({'Status': False, 'Errors': str(error)})
                        else:
                            objects_created += 1

                    else:

                        return JsonResponse({'Status': False, 'Errors': serializer.errors})

            return JsonResponse({'Status': True, 'Создано объектов': objects_created})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # удалить товары из корзины
    def delete(self, request, *args, **kwargs):
        """
                Удалять товары из корзины пользователя.

         """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Не удалось авторизоваться'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # добавить позиции в корзину
    def put(self, request, *args, **kwargs):
        """
                Обновите элементы в корзине пользователя.

                Аргументы:
                - запрос (Request): Объект запроса Django.

                Возвращается:
                - JsonResponse: ответ, указывающий статус операции и любые ошибк
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Не авторизован'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            try:
                items_dict = load_json(items_sting)
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_updated = 0
                for order_item in items_dict:
                    if type(order_item['id']) == int and type(order_item['quantity']) == int:
                        objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                            quantity=order_item['quantity'])

                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerUpdate(APIView):
    """
    Класс для обновления информации о партнере.

    """

    def post(self, request, *args, **kwargs):
        """
                Обновите информацию о прайс-листе партнера.

                Аргументы:
                - запрос (Request): Объект запроса Django.

                Возвращается:
                - JsonResponse: ответ, указывающий статус операции и любые ошибки.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                stream = get(url).content

                data = load_yaml(stream, Loader=Loader)

                shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category_object.shops.add(shop.id)
                    category_object.save()
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for item in data['goods']:
                    product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                    product_info = ProductInfo.objects.create(product_id=product.id,
                                                              external_id=item['id'],
                                                              model=item['model'],
                                                              price=item['price'],
                                                              price_rrc=item['price_rrc'],
                                                              quantity=item['quantity'],
                                                              shop_id=shop.id)
                    for name, value in item['parameters'].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(product_info_id=product_info.id,
                                                        parameter_id=parameter_object.id,
                                                        value=value)

                return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerState(APIView):
    """
        Класс для управления государством-партнером.

        Методы:
        - получить: Получить состояние партнера.

        Атрибуты:
       - None
       """
    # получить текущий статус
    def get(self, request, *args, **kwargs):
        """
                Извлеките состояние партнера.

                Аргументы:
                - запрос (Request): Объект запроса Django.

                Возвращается:
                - Ответ: Ответ, содержащий состояние партнера.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    # изменить текущий статус
    def post(self, request, *args, **kwargs):
        """
               Обновите состояние партнера.

                Аргументы:
                - запрос (Request): Объект запроса Django.

                Возвращается:
                - JsonResponse: ответ, указывающий статус операции и любые ошибки.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class PartnerOrders(APIView):
    """
    Класс для получения заказов поставщиками
     Methods:
    - get: Извлеките заказы, связанные с аутентифицированным партнером.

    Attributes:
    - None
    """

    def get(self, request, *args, **kwargs):
        """
              Извлеките заказы, связанные с аутентифицированным партнером.

                Аргументы:
                - запрос (Request): Объект запроса Django.

                Возвращается:
                - Ответ: Ответ, содержащий заказы, связанные с партнером.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется вход в систему'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)


class ContactView(APIView):
    """
        Класс для управления контактной информацией.

        Методы:
        - get: Извлекает контактную информацию прошедшего проверку пользователя.
        - post: Создает новый контакт для прошедшего проверку пользователя.
        - put: Обновляет контактную информацию прошедшего проверку пользователя.
        - удалить: Удалите контакт аутентифицированного пользователя.

        Атрибуты:
       - None
       """

    # получить мои контакты
    def get(self, request, *args, **kwargs):
        """
                Извлеките контактную информацию аутентифицированного пользователя.

                Аргументы:
                - запрос (Request): Объект запроса Django.

                Возвращается:
                - Ответ: Ответ, содержащий контактную информацию.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        contact = Contact.objects.filter(
            user_id=request.user.id)
        serializer = ContactSerializer(contact, many=True)
        return Response(serializer.data)

    # добавить новый контакт
    def post(self, request, *args, **kwargs):
        """
               Создайте новый контакт для аутентифицированного пользователя.

                Аргументы:
                - request (Запрос): Объект запроса Django.

                Возвращается:
                - JsonResponse: ответ, указывающий статус операции и любые ошибки.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'city', 'street', 'phone'}.issubset(request.data):
            request.data._mutable = True
            request.data.update({'user': request.user.id})
            serializer = ContactSerializer(data=request.data)

            if serializer.is_valid():
                serializer.save()
                return JsonResponse({'Status': True})
            else:
                return JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы city, street, phone'},
                            status=403)

    # удалить контакт
    def delete(self, request, *args, **kwargs):
        """
                Удалите контакт аутентифицированного пользователя.

                Аргументы:
                - запрос (Request): Объект запроса Django.

                Возвращается:
                - JsonResponse: ответ, указывающий статус операции и любые ошибки.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            query = Q()
            objects_deleted = False
            for contact_id in items_list:
                if contact_id.isdigit():
                    query = query | Q(user_id=request.user.id, id=contact_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = Contact.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # редактировать контакт
    def put(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            """
                    Обновите контактную информацию аутентифицированного пользователя.

                    Аргументы:
                    - запрос (Request): Объект запроса Django.

                    Возвращается:
                    - JsonResponse: ответ, указывающий статус операции и любые ошибки.
                   """
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if 'id' in request.data:
            if request.data['id'].isdigit():
                contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
                print(contact)
                if contact:
                    serializer = ContactSerializer(contact, data=request.data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return JsonResponse({'Status': True})
                    else:
                        return JsonResponse({'Status': False, 'Errors': serializer.errors})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})


class OrderView(APIView):

    # получить мои заказы
    def get(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        order = Order.objects.filter(
            user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        serializer_data = OrderSerializer.data
        return JsonResponse({'Status': True, 'order': serializer_data})

    # разместить заказ из корзины
    def post(self, request, *args, **kwargs):

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Требуется вход в систему'}, status=403)

        if {'id', 'contact'}.issubset(request.data):
            if request.data['id'].isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=request.data['id']).update(
                        contact_id=request.data['contact'],
                        state='new')
                except IntegrityError as error:
                    print(error)
                    return JsonResponse({'Status': False, 'Errors': 'Неправильно указаны аргументы'})
                else:
                    if is_updated:
                        new_order.send(sender=self.__class__, user_id=request.user.id)
                        return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

class RestrictedView(APIView):
    def get(self, request, *args, **kwargs):
        return JsonResponse({'message': 'This is a restricted view'}, status=status.HTTP_200_OK)

class check_user_restricted(APIView):
    def get(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return JsonResponse({'Status': True, 'Message': 'Пользователь зарегистрирован'},
                                status=status.HTTP_200_OK)

        else:
            print(request.user.id)
            return JsonResponse({'Status': False, 'Message': 'Пользователь не зарегестрирован'},
                                status=status.HTTP_401_UNAUTHORIZED)