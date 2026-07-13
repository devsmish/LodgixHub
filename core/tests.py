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
        # Dynamically create tables in the test database for stub models.
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(TestBaseModel)
            schema_editor.create_model(TestLogModel)

    @classmethod
    def tearDownClass(cls):
        # Delete the tables after all tests in this class have completed.
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(TestLogModel)
            schema_editor.delete_model(TestBaseModel)
        super().tearDownClass()

    def test_base_model_soft_delete_and_restore(self):
        """Verification of soft deletion and restoration of a single instance."""
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
        """Verification that bulk deletion via QuerySet also performs a soft delete."""
        TestBaseModel.objects.create()
        TestBaseModel.objects.create()

        self.assertEqual(TestBaseModel.objects.count(), 2)

        # Bulk deletion
        TestBaseModel.objects.all().delete()

        self.assertEqual(TestBaseModel.objects.count(), 0)
        self.assertEqual(TestBaseModel.all_objects.count(), 2)

    def test_base_model_delete_and_restore_bump_updated_at(self):
        """Check the updated_at timestamp during instance bulk soft-delete/restore operations"""
        instance = TestBaseModel.objects.create()
        original_updated_at = instance.updated_at

        instance.delete()
        instance.refresh_from_db()
        self.assertGreater(instance.updated_at, original_updated_at)

        updated_at_after_delete = instance.updated_at
        instance.restore()
        instance.refresh_from_db()
        self.assertGreater(instance.updated_at, updated_at_after_delete)

    def test_base_model_bulk_delete_and_restore_bump_updated_at(self):
        """Check the updated_at timestamp during queryset bulk soft-delete/restore operations"""
        a = TestBaseModel.objects.create()
        b = TestBaseModel.objects.create()
        original = {a.pk: a.updated_at, b.pk: b.updated_at}

        TestBaseModel.objects.all().delete()
        for pk, original_updated_at in original.items():
            obj = TestBaseModel.all_objects.get(pk=pk)
            self.assertIsNotNone(obj.deleted_at)
            self.assertGreater(obj.updated_at, original_updated_at)

        after_delete = {
            pk: TestBaseModel.all_objects.get(pk=pk).updated_at for pk in original
        }
        TestBaseModel.all_objects.all().restore()
        for pk, updated_at_after_delete in after_delete.items():
            obj = TestBaseModel.objects.get(pk=pk)
            self.assertIsNone(obj.deleted_at)
            self.assertGreater(obj.updated_at, updated_at_after_delete)

    def test_log_model_immutability(self):
        """Verification that LogModel prevents updates to already created records."""
        log = TestLogModel.objects.create()

        # An attempt to update an existing record should raise a ValidationError.
        with self.assertRaises(ValidationError):
            log.save()

    def test_log_model_instance_delete_protected(self):
        """Verification that LogModel prevents the deletion of a single instance."""
        log = TestLogModel.objects.create()
        with self.assertRaises(ValidationError):
            log.delete()

    def test_log_model_bulk_delete_protected(self):
        """Bulk-delete operations performed via a QuerySet do not bypass LogModel protection
        when deleting data."""
        TestLogModel.objects.create()
        TestLogModel.objects.create()
        self.assertEqual(TestLogModel.objects.count(), 2)

        with self.assertRaises(ValidationError):
            TestLogModel.objects.all().delete()

        self.assertEqual(TestLogModel.objects.count(), 2)

    def test_log_model_purge_escape_hatch_works(self):
        """Operations via the GDPR purge escape hatch should work."""
        TestLogModel.objects.create()
        TestLogModel.objects.create()

        TestLogModel.objects.all().purge()

        self.assertEqual(TestLogModel.objects.count(), 0)
