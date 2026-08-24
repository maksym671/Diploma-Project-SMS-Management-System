from django.db import migrations


def backfill_assigned_by(apps, schema_editor):
    """Attribute grades created before the audit field to the course teacher."""
    Grade = apps.get_model('core', 'Grade')

    updated = []
    for grade in Grade.objects.filter(assigned_by__isnull=True).select_related(
        'enrollment__course__teacher'
    ):
        teacher = grade.enrollment.course.teacher
        if teacher is not None:
            grade.assigned_by = teacher
            updated.append(grade)

    Grade.objects.bulk_update(updated, ['assigned_by'])


def clear_assigned_by(apps, schema_editor):
    apps.get_model('core', 'Grade').objects.update(assigned_by=None)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_grade_assigned_by'),
    ]

    operations = [
        migrations.RunPython(backfill_assigned_by, clear_assigned_by),
    ]
