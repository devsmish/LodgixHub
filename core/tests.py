from django.core.exceptions import ValidationError
from django.db import connection
from django.test import TransactionTestCase

from core.models import BaseModel, LogModel


# Stub models for testing abstract classes
class TestBaseModel(BaseModel):
    class Meta:
        app_label = "core"


class TestLogModel(LogModel):
    class Meta:
        app_label = "core"


class CoreModelsTestCase(TransactionTestCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # Динамически создаем таблицы в тестовой БД для моделей-заглушек
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(TestBaseModel)
            schema_editor.create_model(TestLogModel)

    @classmethod
    def tearDownClass(cls):
        # Удаляем таблицы после завершения всех тестов в этом классе
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(TestLogModel)
            schema_editor.delete_model(TestBaseModel)
        super().tearDownClass()

    def test_base_model_soft_delete_and_restore(self):
        """Проверка логического удаления и восстановления одиночного инстанса."""
        instance = TestBaseModel.objects.create()

        # The object is active by default.
        self.assertIn(instance, TestBaseModel.objects.all())

        # Logical deletion
        instance.delete()
        self.assertIsNotNone(instance.deleted_at)

        # Checking the performance of managers
        self.assertNotIn(instance, TestBaseModel.objects.all())
        self.assertIn(instance, TestBaseModel.all_objects.all())

        # Recovery
        instance.restore()
        self.assertIsNone(instance.deleted_at)
        self.assertIn(instance, TestBaseModel.objects.all())

    def test_base_model_bulk_delete(self):
        """Проверка, что массовое удаление через QuerySet тоже выполняет Soft Delete."""
        TestBaseModel.objects.create()
        TestBaseModel.objects.create()

        self.assertEqual(TestBaseModel.objects.count(), 2)

        # Bulk deletion
        TestBaseModel.objects.all().delete()

        self.assertEqual(TestBaseModel.objects.count(), 0)
        self.assertEqual(TestBaseModel.all_objects.count(), 2)

    def test_log_model_immutability(self):
        """Проверка, что LogModel запрещает обновлять уже созданные записи."""
        log = TestLogModel.objects.create()

        # An attempt to update an existing record should raise a ValidationError.
        with self.assertRaises(ValidationError):
            log.save()
