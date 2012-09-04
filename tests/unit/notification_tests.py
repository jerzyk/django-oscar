from django.core import mail
from django.test import TestCase
from django.contrib.auth.models import User
from django_dynamic_fixture import get

from oscar.apps.catalogue.models import Product, ProductClass
from oscar.apps.partner.models import StockRecord
from oscar.apps.catalogue.notification.models import ProductNotification


class TestANotificationForARegisteredUser(TestCase):

    def setUp(self):
        self.product = get(Product)
        self.user = get(User)
        self.notification = ProductNotification.objects.create(
            user=self.user,
            product=self.product)

    def test_uses_the_users_email_for_notifications(self):
        self.assertEquals(self.notification.get_notification_email(),
                          self.user.email)

    def test_defaults_to_inactive_status(self):
        self.assertFalse(self.notification.is_active())

    def test_defaults_to_unconfirmed(self):
        self.assertFalse(self.notification.is_confirmed())


class TestANotificationForAnAnonymousUser(TestCase):

    def setUp(self):
        self.product = get(Product)
        self.email = 'test@oscarcommerce.com'
        self.notification = ProductNotification.objects.create(
            email=self.email,
            product=self.product)

    def test_uses_the_specified_email_for_notifications(self):
        self.assertEquals(self.notification.get_notification_email(),
                          self.email)


class TestNotificationEmails(TestCase):

    def setUp(self):
        self.product_class = ProductClass.objects.create(name='books')
        self.product = get(Product, product_class=self.product_class,
                           title='product_1', upc='000000000001')
        self.product_2 = get(Product, product_class=self.product_class,
                           title='product_2', upc='000000000002')

        self.user_1 = get(User, email='user@one.com')
        self.user_2 = get(User, email='user@two.com')

        get(StockRecord, product=self.product, num_in_stock=0)

    def test_are_not_sent_when_stock_level_remains_0(self):
        stock_record = StockRecord.objects.get(pk=1)
        self.assertEquals(stock_record.num_in_stock, 0)
        stock_record.save()
        self.assertEquals(stock_record.num_in_stock, 0)

        self.assertEquals(len(mail.outbox), 0)

    def test_are_not_sent_when_there_are_no_notifications(self):
        stock_record = StockRecord.objects.get(pk=1)
        self.assertEquals(stock_record.num_in_stock, 0)

        stock_record.num_in_stock = 20
        stock_record.save()

        self.assertEquals(len(mail.outbox), 0)

    def test_are_sent_correctly_when_there_are_notifications(self):
        ProductNotification.objects.create(user=self.user_1,
                                           product=self.product,
                                           status=ProductNotification.ACTIVE)
        ProductNotification.objects.create(user=self.user_2,
                                           product=self.product,
                                           status=ProductNotification.ACTIVE)
        ProductNotification.objects.create(user=None,
                                           email='anonymous@test.com',
                                           product=self.product,
                                           status=ProductNotification.ACTIVE)
        ProductNotification.objects.create(user=self.user_2,
                                           product=self.product_2,
                                           status=ProductNotification.ACTIVE)
        ProductNotification.objects.create(product=self.product,
                                           status=ProductNotification.INACTIVE)

        stock_record = StockRecord.objects.get(pk=1)
        self.assertEquals(stock_record.num_in_stock, 0)

        stock_record.num_in_stock = 20
        stock_record.save()

        self.assertEquals(len(mail.outbox), 3)
        self.assertItemsEqual(
            [e.to[0] for e in mail.outbox],
            [self.user_1.email, self.user_2.email, 'anonymous@test.com'],
        )

        notification = ProductNotification.objects.get(pk=1)
        self.assertEquals(notification.status, ProductNotification.INACTIVE)
        self.assertNotEquals(notification.date_notified, None)

        notification = ProductNotification.objects.get(pk=2)
        self.assertEquals(notification.status, ProductNotification.INACTIVE)
        self.assertNotEquals(notification.date_notified, None)

        notification = ProductNotification.objects.get(pk=3)
        self.assertEquals(notification.status, ProductNotification.INACTIVE)
        self.assertNotEquals(notification.date_notified, None)

        notification = ProductNotification.objects.get(pk=4)
        self.assertEquals(notification.status, ProductNotification.ACTIVE)
        self.assertEquals(notification.date_notified, None)
