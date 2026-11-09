"""
pytest/pytest-django version, core/tests.py.

Stub models are defined at the module level(just as in the unittest version) — this is important:
they must be registered in the Django app registry during the module import phase, before the
registry is "sealed." The corresponding database tables are created and dropped once per module
using `django_db_blocker`. While the standard `@pytest.mark.django_db` decorator wraps each test
in a transaction that is subsequently rolled back, DDL operations (such as `CREATE TABLE` or
`DROP TABLE`) should not be included in such transactions—doing so is often unsafe.
"""

import pytest
from django.core.exceptions import ValidationError
from django.db import connection

from core.models import BaseModel, LogModel


class StubBaseModel(BaseModel):
    class Meta:
        app_label = "core"


class StubLogModel(LogModel):
    class Meta:
        app_label = "core"


@pytest.fixture(scope="module", autouse=True)
def stub_tables(django_db_blocker):
    """Creates tables for StubBaseModel/StubLogModel once for the entire module,
    and then deletes them."""
    with django_db_blocker.unblock():
        with connection.schema_editor() as schema_editor:
            schema_editor.create_model(StubBaseModel)
            schema_editor.create_model(StubLogModel)

    yield

    with django_db_blocker.unblock():
        with connection.schema_editor() as schema_editor:
            schema_editor.delete_model(StubLogModel)
            schema_editor.delete_model(StubBaseModel)


# BaseModel — soft delete / restore


@pytest.mark.django_db
def test_base_model_created_active_by_default():
    instance = StubBaseModel.objects.create()

    assert instance.deleted_at is None
    assert instance.is_deleted is False
    assert instance in StubBaseModel.objects.all()


@pytest.mark.django_db
def test_base_model_soft_delete_and_restore_single_instance():
    """Logical deletion and restoration of a single instance."""
    instance = StubBaseModel.objects.create()

    instance.delete()
    assert instance.deleted_at is not None
    assert instance.is_deleted is True

    # objects (the default manager) no longer sees the deleted record,
    # while all_objects does see.
    assert instance not in StubBaseModel.objects.all()
    assert instance in StubBaseModel.all_objects.all()

    instance.restore()
    assert instance.deleted_at is None
    assert instance in StubBaseModel.objects.all()


@pytest.mark.django_db
def test_base_model_bulk_delete_and_restore_via_queryset():
    """Bulk deletion/restoration via QuerySet should also be a soft delete."""
    StubBaseModel.objects.create()
    StubBaseModel.objects.create()
    assert StubBaseModel.objects.count() == 2

    StubBaseModel.objects.all().delete()
    assert StubBaseModel.objects.count() == 0
    assert StubBaseModel.all_objects.count() == 2

    StubBaseModel.all_objects.all().restore()
    assert StubBaseModel.objects.count() == 2


@pytest.mark.django_db
def test_base_model_instance_delete_and_restore_bump_updated_at():
    """Regression: bulk and instance soft-delete/restore operations must update `updated_at`."""
    instance = StubBaseModel.objects.create()
    original_updated_at = instance.updated_at

    instance.delete()
    instance.refresh_from_db()
    assert instance.updated_at > original_updated_at

    updated_at_after_delete = instance.updated_at
    instance.restore()
    instance.refresh_from_db()
    assert instance.updated_at > updated_at_after_delete


@pytest.mark.django_db
def test_base_model_bulk_delete_and_restore_bump_updated_at():
    """The same thing, but using queryset operations instead of an instance."""
    a = StubBaseModel.objects.create()
    b = StubBaseModel.objects.create()
    original = {a.pk: a.updated_at, b.pk: b.updated_at}

    StubBaseModel.objects.all().delete()
    after_delete = {}
    for pk, original_updated_at in original.items():
        obj = StubBaseModel.all_objects.get(pk=pk)
        assert obj.deleted_at is not None
        assert obj.updated_at > original_updated_at
        after_delete[pk] = obj.updated_at

    StubBaseModel.all_objects.all().restore()
    for pk, updated_at_after_delete in after_delete.items():
        obj = StubBaseModel.objects.get(pk=pk)
        assert obj.deleted_at is None
        assert obj.updated_at > updated_at_after_delete


@pytest.mark.django_db
def test_base_model_hard_delete_removes_row_physically():
    instance = StubBaseModel.objects.create()
    pk = instance.pk

    instance.hard_delete()

    assert not StubBaseModel.all_objects.filter(pk=pk).exists()


# LogModel — append-only / immutability


@pytest.mark.django_db
def test_log_model_create_succeeds():
    log = StubLogModel.objects.create()
    assert StubLogModel.objects.filter(pk=log.pk).exists()


@pytest.mark.django_db
def test_log_model_resave_raises():
    """Calling `save()` again on an existing record is prohibited — this enforces
    immutability at the instance level."""
    log = StubLogModel.objects.create()

    with pytest.raises(ValidationError):
        log.save()


@pytest.mark.django_db
def test_log_model_instance_delete_raises_and_keeps_row():
    log = StubLogModel.objects.create()

    with pytest.raises(ValidationError):
        log.delete()

    assert StubLogModel.objects.filter(pk=log.pk).exists()


@pytest.mark.django_db
def test_log_model_bulk_delete_raises_and_keeps_rows():
    """
    Regression regarding a discovered bug: bulk-delete operations via QuerySet previously
    bypassed LogModel protection, physically deleting rows while circumventing the
    instance-level delete() method.
    """
    StubLogModel.objects.create()
    StubLogModel.objects.create()
    assert StubLogModel.objects.count() == 2

    with pytest.raises(ValidationError):
        StubLogModel.objects.all().delete()

    assert StubLogModel.objects.count() == 2


@pytest.mark.django_db
def test_log_model_queryset_update_raises_and_keeps_rows():
    """
    .update() performs a direct SQL UPDATE, bypassing save(); consequently, the
    instance-level protection defined in LogModel.save() does not detect it. A separate
    override at the LogQuerySet level is required.
    """
    log = StubLogModel.objects.create()

    with pytest.raises(ValidationError):
        StubLogModel.objects.filter(pk=log.pk).update(created_at=log.created_at)

    assert StubLogModel.objects.count() == 1


@pytest.mark.django_db
def test_log_model_bulk_update_method_raises_and_keeps_rows():
    """
    `bulk_update()` is a Django implementation separate from `update()` (performing multiple
    `UPDATE` operations via `CASE WHEN` in batches); `update()` does not intercept it, so a
    custom override in `LogQuerySet` is required.
    """
    log = StubLogModel.objects.create()
    log.created_at = log.created_at

    with pytest.raises(ValidationError):
        StubLogModel.objects.bulk_update([log], fields=["created_at"])

    assert StubLogModel.objects.count() == 1


@pytest.mark.django_db
def test_log_model_purge_queryset_escape_hatch_works():
    """purge() — an explicit, purpose-named protection bypass for retention/GDPR jobs."""
    StubLogModel.objects.create()
    StubLogModel.objects.create()
    assert StubLogModel.objects.count() == 2

    StubLogModel.objects.all().purge()

    assert StubLogModel.objects.count() == 0


@pytest.mark.django_db
def test_log_model_hard_delete_instance_escape_hatch_works():
    """hard_delete() is the instance-equivalent of purge() — it serves the same
    retention/GDPR-only use case."""
    log = StubLogModel.objects.create()
    pk = log.pk

    log.hard_delete()

    assert not StubLogModel.objects.filter(pk=pk).exists()
