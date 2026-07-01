# staff/migrations/0002_eventtemplaterole.py
from django.db import migrations, models
import django.db.models.deletion

class Migration(migrations.Migration):
    dependencies = [('staff', '0001_initial')]
    operations = [
        migrations.CreateModel(
            name='EventTemplateRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('count', models.PositiveIntegerField(default=1)),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='staff.role')),
                ('template', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='template_roles', to='staff.eventtemplate')),
            ],
            options={'ordering': ['role__name'], 'unique_together': {('template', 'role')}},),
    ]