from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('jobs', '0003_remove_jobposting_stack_count_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='jobpostingstack',
            name='job_stack_count',
        ),
    ]
