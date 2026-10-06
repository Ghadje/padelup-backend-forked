from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('app', '0014_alter_booking_status_alter_communitypost_category_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='DeviceToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.CharField(max_length=500, unique=True)),
                ('device_type', models.CharField(choices=[('ios', 'iOS'), ('android', 'Android'), ('web', 'Web')], default='android', max_length=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='device_tokens', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-updated_at'],
            },
        ),
        migrations.AddField(
            model_name='notification',
            name='club',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='notifications', to='app.club'),
        ),
        migrations.AddField(
            model_name='notification',
            name='target',
            field=models.CharField(choices=[('mobile', 'Mobile'), ('dashboard', 'Dashboard'), ('both', 'Tous')], default='mobile', max_length=10),
        ),
        migrations.AlterField(
            model_name='notification',
            name='type',
            field=models.CharField(choices=[('match_invite', 'Invitation au match'), ('match_reminder', 'Rappel de match'), ('match_accepted', 'Match accepté'), ('match_cancelled', 'Match annulé'), ('friend_request', "Demande d'ami"), ('friend_accepted', "Demande d'ami acceptée"), ('achievement', 'Succès déverrouillé'), ('booking_confirmed', 'Réservation confirmée'), ('new_booking', 'Nouvelle réservation'), ('booking_cancelled', 'Réservation annulée')], max_length=20),
        ),
    ]
