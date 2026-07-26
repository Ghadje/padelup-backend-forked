from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags


def send_booking_confirmation(user, booking):
    """Send booking confirmation email in French"""
    court_name = booking.court.name
    club_name = booking.court.club.name

    months = {
        1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril', 5: 'mai', 6: 'juin',
        7: 'juillet', 8: 'août', 9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
    }
    days = {
        0: 'lundi', 1: 'mardi', 2: 'mercredi', 3: 'jeudi', 4: 'vendredi', 5: 'samedi', 6: 'dimanche'
    }

    date_obj = booking.date
    day_name = days[date_obj.weekday()]
    month_name = months[date_obj.month]
    date_str = f"{day_name} {date_obj.day} {month_name} {date_obj.year}"

    start_time = booking.start_time.strftime('%H:%M')
    end_time = booking.end_time.strftime('%H:%M')

    subject = f'Réservation confirmée - {club_name}'
    html_content = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 24px;">
        <div style="background: #094A73; color: white; padding: 24px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">PadelUp</h1>
            <p style="margin: 8px 0 0; opacity: 0.9;">Confirmation de réservation</p>
        </div>
        <div style="background: white; padding: 24px; border-radius: 0 0 16px 16px;">
            <p>Bonjour <strong>{user.first_name or user.username}</strong>,</p>
            <p>Votre réservation de terrain a été confirmée !</p>
            <div style="background: #f0fdf4; border: 1px solid #10B981; border-radius: 12px; padding: 16px; margin: 16px 0;">
                <h3 style="margin: 0 0 12px; color: #094A73;">{club_name}</h3>
                <p style="margin: 4px 0;"><strong>Terrain :</strong> {court_name}</p>
                <p style="margin: 4px 0;"><strong>Date :</strong> {date_str}</p>
                <p style="margin: 4px 0;"><strong>Heure :</strong> {start_time} - {end_time}</p>
                <p style="margin: 4px 0;"><strong>Durée :</strong> {booking.duration} min</p>
                <p style="margin: 4px 0;"><strong>Total :</strong> {booking.total_amount} {booking.currency}</p>
            </div>
            <p style="color: #6b7280; font-size: 14px;">À bientôt sur les terrains !</p>
            <p style="color: #6b7280; font-size: 14px;">L'équipe PadelUp</p>
        </div>
    </div>
    """

    return _send_email(user.email, subject, html_content)


def send_booking_confirmation_fr(user, booking):
    """Send booking confirmation email in French"""
    court_name = booking.court.name
    club_name = booking.court.club.name
    
    months = {
        1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril', 5: 'mai', 6: 'juin',
        7: 'juillet', 8: 'août', 9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
    }
    days = {
        0: 'lundi', 1: 'mardi', 2: 'mercredi', 3: 'jeudi', 4: 'vendredi', 5: 'samedi', 6: 'dimanche'
    }
    
    date_obj = booking.date
    day_name = days[date_obj.weekday()]
    month_name = months[date_obj.month]
    date_str = f"{day_name} {date_obj.day} {month_name} {date_obj.year}"
    
    start_time = booking.start_time.strftime('%H:%M')
    end_time = booking.end_time.strftime('%H:%M')

    subject = f'Réservation Confirmée - {club_name}'
    html_content = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 24px;">
        <div style="background: #094A73; color: white; padding: 24px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">PadelUp</h1>
            <p style="margin: 8px 0 0; opacity: 0.9;">Confirmation de Réservation</p>
        </div>
        <div style="background: white; padding: 24px; border-radius: 0 0 16px 16px;">
            <p>Bonjour <strong>{user.first_name or user.username}</strong>,</p>
            <p>Votre réservation de terrain a été confirmée !</p>
            <div style="background: #f0fdf4; border: 1px solid #10B981; border-radius: 12px; padding: 16px; margin: 16px 0;">
                <h3 style="margin: 0 0 12px; color: #094A73;">{club_name}</h3>
                <p style="margin: 4px 0;"><strong>Terrain :</strong> {court_name}</p>
                <p style="margin: 4px 0;"><strong>Date :</strong> {date_str}</p>
                <p style="margin: 4px 0;"><strong>Heure :</strong> {start_time} - {end_time}</p>
                <p style="margin: 4px 0;"><strong>Durée :</strong> {booking.duration} min</p>
                <p style="margin: 4px 0;"><strong>Total :</strong> {booking.total_amount} {booking.currency}</p>
            </div>
            <p style="color: #6b7280; font-size: 14px;">À bientôt sur les terrains !</p>
            <p style="color: #6b7280; font-size: 14px;">L'équipe PadelUp</p>
        </div>
    </div>
    """

    return _send_email(user.email, subject, html_content)


def send_match_join_confirmation(user, match):
    """Send match join confirmation email in French"""
    months = {
        1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril', 5: 'mai', 6: 'juin',
        7: 'juillet', 8: 'août', 9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
    }
    days = {
        0: 'lundi', 1: 'mardi', 2: 'mercredi', 3: 'jeudi', 4: 'vendredi', 5: 'samedi', 6: 'dimanche'
    }

    if hasattr(match, 'date'):
        date_obj = match.date
    elif hasattr(match, 'date_time'):
        date_obj = match.date_time.date()
    else:
        date_obj = None

    if date_obj:
        day_name = days[date_obj.weekday()]
        month_name = months[date_obj.month]
        date_str = f"{day_name} {date_obj.day} {month_name} {date_obj.year}"
    else:
        date_str = ''

    if hasattr(match, 'time'):
        time_str = match.time.strftime('%H:%M')
    elif hasattr(match, 'date_time'):
        time_str = match.date_time.strftime('%H:%M')
    else:
        time_str = ''

    match_type = match.get_match_type_display() if hasattr(match, 'get_match_type_display') else match.match_type.capitalize()

    subject = f'Match rejoint - {match.title}'
    html_content = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 24px;">
        <div style="background: #094A73; color: white; padding: 24px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">PadelUp</h1>
            <p style="margin: 8px 0 0; opacity: 0.9;">Confirmation du match</p>
        </div>
        <div style="background: white; padding: 24px; border-radius: 0 0 16px 16px;">
            <p>Bonjour <strong>{user.first_name or user.username}</strong>,</p>
            <p>Vous avez rejoint un match avec succès !</p>
            <div style="background: #eff6ff; border: 1px solid #3b82f6; border-radius: 12px; padding: 16px; margin: 16px 0;">
                <h3 style="margin: 0 0 12px; color: #094A73;">{match.title}</h3>
                <p style="margin: 4px 0;"><strong>Type :</strong> {match_type}</p>
                <p style="margin: 4px 0;"><strong>Date :</strong> {date_str}</p>
                <p style="margin: 4px 0;"><strong>Heure :</strong> {time_str}</p>
                <p style="margin: 4px 0;"><strong>Organisateur :</strong> {match.organizer.username}</p>
                <p style="margin: 4px 0;"><strong>Joueurs :</strong> {match.get_accepted_participants_count()}/{match.max_players}</p>
            </div>
            <p style="color: #6b7280; font-size: 14px;">Bonne chance et bon match !</p>
            <p style="color: #6b7280; font-size: 14px;">L'équipe PadelUp</p>
        </div>
    </div>
    """

    return _send_email(user.email, subject, html_content)


def send_welcome_email(user):
    """Send welcome email after registration"""
    subject = 'Bienvenue sur PadelUp !'
    html_content = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 24px;">
        <div style="background: #094A73; color: white; padding: 24px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">PadelUp</h1>
            <p style="margin: 8px 0 0; opacity: 0.9;">Bienvenue dans la communauté !</p>
        </div>
        <div style="background: white; padding: 24px; border-radius: 0 0 16px 16px;">
            <p>Bonjour <strong>{user.first_name or user.username}</strong>,</p>
            <p>Votre compte PadelUp a été créé avec succès ! 🎾</p>
            <div style="background: #f0fdf4; border: 1px solid #10B981; border-radius: 12px; padding: 16px; margin: 16px 0;">
                <h3 style="margin: 0 0 12px; color: #094A73;">Pour commencer</h3>
                <p style="margin: 4px 0;">✅ Complétez votre profil avec votre niveau</p>
                <p style="margin: 4px 0;">✅ Découvrez les clubs près de chez vous</p>
                <p style="margin: 4px 0;">✅ Rejoignez ou créez un match</p>
                <p style="margin: 4px 0;">✅ Ajoutez des amis et jouez ensemble</p>
            </div>
            <p style="color: #6b7280; font-size: 14px;">À bientôt sur les terrains !</p>
            <p style="color: #6b7280; font-size: 14px;">L'équipe PadelUp</p>
        </div>
    </div>
    """

    return _send_email(user.email, subject, html_content)


def send_password_reset_email(user, code):
    """Send password reset code via email"""
    subject = 'PadelUp - Code de réinitialisation'
    html_content = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 24px;">
        <div style="background: #094A73; color: white; padding: 24px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">PadelUp</h1>
            <p style="margin: 8px 0 0; opacity: 0.9;">Réinitialisation du mot de passe</p>
        </div>
        <div style="background: white; padding: 24px; border-radius: 0 0 16px 16px;">
            <p>Bonjour <strong>{user.first_name or user.username}</strong>,</p>
            <p>Vous avez demandé la réinitialisation de votre mot de passe. Voici votre code de vérification :</p>
            <div style="background: #eff6ff; border: 1px solid #3b82f6; border-radius: 12px; padding: 24px; margin: 16px 0; text-align: center;">
                <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #094A73; margin: 0;">{code}</p>
            </div>
            <p style="color: #6b7280; font-size: 14px;">Ce code est valable pendant <strong>15 minutes</strong>.</p>
            <p style="color: #6b7280; font-size: 14px;">Si vous n'avez pas demandé cette réinitialisation, ignorez cet email.</p>
        </div>
    </div>
    """

    return _send_email(user.email, subject, html_content)


def send_verification_email(user, code):
    """Send registration verification code via email"""
    subject = 'PadelUp - Code de confirmation d\'inscription'
    html_content = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 24px;">
        <div style="background: #094A73; color: white; padding: 24px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">PadelUp</h1>
            <p style="margin: 8px 0 0; opacity: 0.9;">Confirmation de votre inscription</p>
        </div>
        <div style="background: white; padding: 24px; border-radius: 0 0 16px 16px;">
            <p>Bonjour <strong>{user.first_name or user.username}</strong>,</p>
            <p>Merci de vous être inscrit sur PadelUp ! Pour valider votre inscription, veuillez saisir le code de confirmation suivant dans l'application :</p>
            <div style="background: #eff6ff; border: 1px solid #3b82f6; border-radius: 12px; padding: 24px; margin: 16px 0; text-align: center;">
                <p style="font-size: 32px; font-weight: bold; letter-spacing: 8px; color: #094A73; margin: 0;">{code}</p>
            </div>
            <p style="color: #6b7280; font-size: 14px;">Ce code est valable pendant <strong>24 heures</strong>.</p>
            <p style="color: #6b7280; font-size: 14px;">Si vous n'avez pas initié cette inscription, vous pouvez ignorer cet email.</p>
        </div>
    </div>
    """

    return _send_email(user.email, subject, html_content)


def _send_email(to_email, subject, html_content):
    """Send an email using Django's configured mail backend"""
    try:
        text_content = strip_tags(html_content)
        msg = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[to_email],
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        print(f'Email sent to {to_email}')
        return True
    except Exception as e:
        print(f'Failed to send email to {to_email}: {e}')
        return False
