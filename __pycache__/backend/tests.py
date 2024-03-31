from django.test import TestCase



from django.contrib.auth.models import User


from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from backend.forms import ShopForm, ProductSearchForm, CustomUserCreationForm
from backend.models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, \
    Contact, ConfirmEmailToken, User
from backend.serializers import UserSerializer, CategorySerializer, ShopSerializer, ProductInfoSerializer, \
    OrderItemSerializer, OrderSerializer, ContactSerializer
from backend.signals import new_user_registered, new_order

# Create your tests here.

class PartnerStateTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('partner-state')  # Предположим, что у вас есть URL для представления
        self.shop_user = User.objects.create_user(username='shop_user', email='shop@example.com', password='password')
        self.shop_user.type = 'shop'
        self.shop_user.save()

    def test_get_partner_state_unauthenticated(self):
        # Отправляем GET-запрос без аутентификации
        response = self.client.get(self.url)

        # Проверяем, что запрос завершается с кодом 403 (Forbidden)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверяем, что возвращается сообщение о необходимости входа в систему
        self.assertEqual(response.data, {'Status': False, 'Error': 'Log in required'})

    def test_get_partner_state_wrong_user_type(self):
        # Аутентифицируемся как пользователь с неправильным типом
        self.client.force_login(User.objects.create_user(username='test_user', email='test@example.com', password='password'))

        # Отправляем GET-запрос
        response = self.client.get(self.url)

        # Проверяем, что запрос завершается с кодом 403 (Forbidden)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверяем, что возвращается сообщение о доступе только для магазинов
        self.assertEqual(response.data, {'Status': False, 'Error': 'Только для магазинов'})

    def test_get_partner_state_authenticated(self):
        # Аутентифицируемся как магазин
        self.client.force_login(self.shop_user)

        # Отправляем GET-запрос
        response = self.client.get(self.url)

        # Проверяем, что запрос завершается с кодом 200 (OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получаем объект магазина из базы данных
        shop = Shop.objects.get(user=self.shop_user)

        # Создаем сериализатор для магазина
        serializer = ShopSerializer(shop)

        # Проверяем, что данные, возвращенные в ответе, соответствуют ожидаемым данным
        self.assertEqual(response.data, serializer.data)

    def test_change_partner_state_authenticated(self):
        # Аутентифицируемся как магазин
        self.client.force_login(self.shop_user)

        # Подготавливаем данные для отправки POST-запроса
        data = {'state': 'True'}

        # Отправляем POST-запрос
        response = self.client.post(self.url, data)

        # Проверяем, что запрос завершается с кодом 200 (OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем, что возвращается сообщение о успешном изменении статуса
        self.assertEqual(response.data, {'Status': True})

        # Проверяем, что статус магазина действительно изменился в базе данных
        self.assertTrue(Shop.objects.get(user=self.shop_user).state)


class ProductInfoViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('product')  # Предположим, что у вас есть URL для представления

        # Создаем тестовые данные
        # Создайте тестовые объекты ProductInfo в соответствии с вашей моделью

    def test_get_product_info(self):
        # Отправляем GET-запрос
        response = self.client.get(self.url, {'shop_id': 1,
                                              'category_id': 1})  # Предположим, что у вас есть id магазина и категории

        # Проверяем, что запрос завершился успешно (код 200)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получаем данные из базы данных в соответствии с переданными параметрами
        queryset = ProductInfo.objects.filter(shop_id=1, product__category_id=1).select_related(
            'shop', 'product__category').prefetch_related(
            'product_parameters__parameter').distinct()

        # Создаем сериализатор для полученных данных
        serializer = ProductInfoSerializer(queryset, many=True)

        # Проверяем, что данные, возвращенные в ответе, соответствуют ожидаемым данным
        self.assertEqual(response.data, serializer.data)


class RegisterAccountTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('register_users')

    def test_register_account_success(self):
        # Подготавливаем данные для успешной регистрации
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'password': 'testpassword123',
            'company': 'Example Company',
            'position': 'Developer'
        }

        # Отправляем POST-запрос
        response = self.client.post(self.register_url, data, format='json')

        # Проверяем, что запрос завершился успешно и пользователь был зарегистрирован
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['Status'])

    def test_register_account_missing_arguments(self):
        # Подготавливаем данные с отсутствующими обязательными аргументами
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            # Отсутствуют другие обязательные аргументы
        }

        # Отправляем POST-запрос
        response = self.client.post(self.register_url, data, format='json')

        # Проверяем, что запрос завершился с ошибкой и возвращается соответствующее сообщение об ошибке
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['Status'])

    def test_register_account_weak_password(self):
        # Подготавливаем данные с слабым паролем
        data = {
            'first_name': 'John',
            'last_name': 'Doe',
            'email': 'john.doe@example.com',
            'password': 'weak',
            'company': 'Example Company',
            'position': 'Developer'
        }

        # Отправляем POST-запрос
        response = self.client.post(self.register_url, data, format='json')

        # Проверяем, что запрос завершился с ошибкой и возвращается соответствующее сообщение об ошибке
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(response.data['Status'])


class LoginAccountTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.login_url = 'user/login'

        # Создаем тестового пользователя для авторизации
        self.test_user = User.objects.create_user(username='testuser', email='test@example.com', password='testpassword')

    def test_login_account_success(self):
        # Подготавливаем данные для успешной авторизации
        data = {
            'email': 'test@example.com',
            'password': 'testpassword'
        }

        # Отправляем POST-запрос
        response = self.client.post(self.login_url, data, format='json')

        # Проверяем, что запрос завершился успешно и возвращается токен
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue('Token' in response.data)

    def test_login_account_missing_arguments(self):
        # Подготавливаем данные с отсутствующими обязательными аргументами
        data = {
            'email': 'test@example.com',
            # Отсутствует пароль
        }

        # Отправляем POST-запрос
        response = self.client.post(self.login_url, data, format='json')

        # Проверяем, что запрос завершился с ошибкой и возвращается соответствующее сообщение об ошибке
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse('Token' in response.data)

    def test_login_account_invalid_credentials(self):
        # Подготавливаем данные с неверными учетными данными
        data = {
            'email': 'test@example.com',
            'password': 'incorrectpassword'
        }

        # Отправляем POST-запрос
        response = self.client.post(self.login_url, data, format='json')

        # Проверяем, что запрос завершился с ошибкой и возвращается соответствующее сообщение об ошибке
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse('Token' in response.data)


class CategoryViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('categories')

        # Создаем тестовые данные
        Category.objects.create(name='Category 1')
        Category.objects.create(name='Category 2')

    def test_list_categories(self):
        # Отправляем GET-запрос
        response = self.client.get(self.url)

        # Проверяем, что запрос завершился успешно (код 200)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Получаем список категорий из базы данных
        categories = Category.objects.all()
        serializer = CategorySerializer(categories, many=True)

        # Проверяем, что данные, возвращенные в ответе, соответствуют ожидаемым данным
        self.assertEqual(response.data, serializer.data)


class OrderViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('order')  # Предположим, что у вас есть URL для представления
        self.user = User.objects.create_user(username='testuser', email='test@example.com', password='testpassword')
        self.client.force_authenticate(user=self.user)

    def test_get_orders(self):
        # Создайте тестовые объекты Order, связанные с текущим пользователем self.user

        # Отправляем GET-запрос
        response = self.client.get(self.url)

        # Проверяем, что запрос завершился успешно (код 200)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем, что заказы возвращаются только для аутентифицированного пользователя
        self.assertTrue(response.data['Status'])
        self.assertIsNotNone(response.data['order'])

    def test_place_order(self):
        # Подготавливаем данные для размещения заказа
        data = {
            'id': 1,  # Предположим, что у вас есть заказ с id=1, который находится в корзине
            'contact': 1,  # Предположим, что id контакта равен 1
        }

        # Отправляем POST-запрос
        response = self.client.post(self.url, data, format='json')

        # Проверяем, что запрос завершился успешно (код 200)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем, что заказ успешно размещен
        self.assertTrue(response.data['Status'])


class ShopViewTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('shops')
        self.active_shop = Shop.objects.create(name='Active Shop', state=True)
        self.inactive_shop = Shop.objects.create(name='Inactive Shop', state=False)

    def test_get_active_shops(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Извлекаем список магазинов из ключа 'results'
        actual_shops = response.data.get('results', [])

        # Получаем активные магазины из базы данных
        active_shops = Shop.objects.filter(state=True)
        serializer = ShopSerializer(active_shops, many=True)

        self.assertEqual(actual_shops, serializer.data)


class PartnerOrdersTest(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.url = reverse('partner-orders')  # Предположим, что у вас есть URL для представления
        self.shop_user = User.objects.create_user(username='shop_user', email='shop@example.com', password='password')
        self.shop_user.type = 'shop'
        self.shop_user.save()

    def test_get_partner_orders_unauthenticated(self):
        # Отправляем GET-запрос без аутентификации
        response = self.client.get(self.url)

        # Проверяем, что запрос завершается с кодом 403 (Forbidden)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверяем, что возвращается сообщение об ошибке о необходимости входа в систему
        self.assertEqual(response.data, {'Status': False, 'Error': 'Требуется вход в систему'})

    def test_get_partner_orders_wrong_user_type(self):
        # Аутентифицируемся как пользователь с неправильным типом
        self.client.force_login(User.objects.create_user(username='test_user', email='test@example.com', password='password'))

        # Отправляем GET-запрос
        response = self.client.get(self.url)

        # Проверяем, что запрос завершается с кодом 403 (Forbidden)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # Проверяем, что возвращается сообщение об ошибке о доступе только для магазинов
        self.assertEqual(response.data, {'Status': False, 'Error': 'Только для магазинов'})

    def test_get_partner_orders_authenticated(self):
        # Аутентифицируемся как магазин
        self.client.force_login(self.shop_user)

        # Отправляем GET-запрос
        response = self.client.get(self.url)

        # Проверяем, что запрос завершается с кодом 200 (OK)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # Проверяем, что возвращаемые данные соответствуют ожидаемым данным заказов магазина
        expected_orders = Order.objects.filter(ordered_items__product_info__shop__user_id=self.shop_user.id).exclude(state='basket').distinct()
        serializer = OrderSerializer(expected_orders, many=True)
        self.assertEqual(response.data, serializer.data)