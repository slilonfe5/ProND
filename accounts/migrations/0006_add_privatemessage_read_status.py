from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_sessionrequest_proposed_capacity_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='privatemessage',
            name='is_read',
            field=models.BooleanField(default=False),
        ),
    ]
