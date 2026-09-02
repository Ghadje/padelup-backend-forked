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


def _format_match_details(match):
    """Helper to extract and format match details in French"""
    months = {
        1: 'janvier', 2: 'février', 3: 'mars', 4: 'avril', 5: 'mai', 6: 'juin',
        7: 'juillet', 8: 'août', 9: 'septembre', 10: 'octobre', 11: 'novembre', 12: 'décembre'
    }
    days = {
        0: 'lundi', 1: 'mardi', 2: 'mercredi', 3: 'jeudi', 4: 'vendredi', 5: 'samedi', 6: 'dimanche'
    }

    if hasattr(match, 'date') and match.date:
        date_obj = match.date
    elif hasattr(match, 'date_time') and match.date_time:
        date_obj = match.date_time.date()
    else:
        date_obj = None

    if date_obj:
        day_name = days[date_obj.weekday()]
        month_name = months[date_obj.month]
        date_str = f"{day_name} {date_obj.day} {month_name} {date_obj.year}"
    else:
        date_str = ''

    if hasattr(match, 'time') and match.time:
        time_str = match.time.strftime('%H:%M')
    elif hasattr(match, 'date_time') and match.date_time:
        time_str = match.date_time.strftime('%H:%M')
    else:
        time_str = ''

    club_name = match.club.name if hasattr(match, 'club') and match.club else 'Club de Padel'
    club_city = match.club.city if hasattr(match, 'club') and match.club and hasattr(match.club, 'city') else ''
    court_name = match.court.name if hasattr(match, 'court') and match.court else ''
    match_type = match.get_match_type_display() if hasattr(match, 'get_match_type_display') else str(getattr(match, 'match_type', 'casual')).capitalize()

    # Calculate participant count
    if hasattr(match, 'get_accepted_participants_count'):
        players_count = match.get_accepted_participants_count()
    elif hasattr(match, 'participants'):
        players_count = match.participants.filter(status='confirmed').count() + 1
    else:
        players_count = 1

    return {
        'date_str': date_str,
        'time_str': time_str,
        'club_name': club_name,
        'club_city': club_city,
        'court_name': court_name,
        'match_type': match_type,
        'players_count': players_count,
        'max_players': getattr(match, 'max_players', 4),
        'duration': getattr(match, 'duration', 60),
        'share_code': getattr(match, 'share_code', ''),
        'organizer_name': match.organizer.username if hasattr(match, 'organizer') and match.organizer else '',
    }


def send_match_creation_confirmation(user, match):
    """Send match creation confirmation email to the organizer in French"""
    info = _format_match_details(match)
    subject = f'Match créé - {match.title}'

    share_code_html = ""
    if info['share_code']:
        share_code_html = f"<p style='margin: 4px 0;'><strong>Code de partage :</strong> <span style='background: #e2e8f0; padding: 2px 6px; border-radius: 4px; font-weight: bold;'>{info['share_code']}</span></p>"

    court_html = f"<p style='margin: 4px 0;'><strong>Terrain :</strong> {info['court_name']}</p>" if info['court_name'] else ""

    html_content = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 24px;">
        <div style="background: #094A73; color: white; padding: 24px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">PadelUp</h1>
            <p style="margin: 8px 0 0; opacity: 0.9;">Votre match a été créé avec succès ! 🎾</p>
        </div>
        <div style="background: white; padding: 24px; border-radius: 0 0 16px 16px;">
            <p>Bonjour <strong>{user.first_name or user.username}</strong>,</p>
            <p>Votre match est maintenant en ligne et prêt à accueillir des joueurs.</p>
            <div style="background: #f0fdf4; border: 1px solid #10B981; border-radius: 12px; padding: 16px; margin: 16px 0;">
                <h3 style="margin: 0 0 12px; color: #094A73;">{match.title}</h3>
                <p style="margin: 4px 0;"><strong>Club :</strong> {info['club_name']}{f" ({info['club_city']})" if info['club_city'] else ''}</p>
                {court_html}
                <p style="margin: 4px 0;"><strong>Type :</strong> {info['match_type']}</p>
                <p style="margin: 4px 0;"><strong>Date :</strong> {info['date_str']}</p>
                <p style="margin: 4px 0;"><strong>Heure :</strong> {info['time_str']} ({info['duration']} min)</p>
                <p style="margin: 4px 0;"><strong>Joueurs :</strong> {info['players_count']}/{info['max_players']}</p>
                {share_code_html}
            </div>
            <p style="color: #6b7280; font-size: 14px;">Vous recevrez une notification par email dès qu'un joueur rejoindra votre match.</p>
            <p style="color: #6b7280; font-size: 14px;">L'équipe PadelUp</p>
        </div>
    </div>
    """

    return _send_email(user.email, subject, html_content)


def send_match_join_confirmation(user, match):
    """Send match join confirmation email to the joining player in French"""
    info = _format_match_details(match)
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
                <p style="margin: 4px 0;"><strong>Club :</strong> {info['club_name']}{f" ({info['club_city']})" if info['club_city'] else ''}</p>
                <p style="margin: 4px 0;"><strong>Type :</strong> {info['match_type']}</p>
                <p style="margin: 4px 0;"><strong>Date :</strong> {info['date_str']}</p>
                <p style="margin: 4px 0;"><strong>Heure :</strong> {info['time_str']}</p>
                <p style="margin: 4px 0;"><strong>Organisateur :</strong> {info['organizer_name']}</p>
                <p style="margin: 4px 0;"><strong>Joueurs :</strong> {info['players_count']}/{info['max_players']}</p>
            </div>
            <p style="color: #6b7280; font-size: 14px;">Bonne chance et bon match !</p>
            <p style="color: #6b7280; font-size: 14px;">L'équipe PadelUp</p>
        </div>
    </div>
    """

    return _send_email(user.email, subject, html_content)


def send_player_joined_organizer_email(organizer, player, match):
    """Send notification email to match organizer when a player joins"""
    info = _format_match_details(match)
    player_name = player.first_name or player.username
    subject = f'Nouveau joueur - {player_name} a rejoint votre match'

    html_content = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 24px;">
        <div style="background: #094A73; color: white; padding: 24px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">PadelUp</h1>
            <p style="margin: 8px 0 0; opacity: 0.9;">Un nouveau joueur a rejoint votre match ! 🎾</p>
        </div>
        <div style="background: white; padding: 24px; border-radius: 0 0 16px 16px;">
            <p>Bonjour <strong>{organizer.first_name or organizer.username}</strong>,</p>
            <p><strong>{player_name}</strong> (@{player.username}) vient de rejoindre votre match <strong>"{match.title}"</strong>.</p>
            <div style="background: #eff6ff; border: 1px solid #3b82f6; border-radius: 12px; padding: 16px; margin: 16px 0;">
                <h3 style="margin: 0 0 12px; color: #094A73;">{match.title}</h3>
                <p style="margin: 4px 0;"><strong>Club :</strong> {info['club_name']}{f" ({info['club_city']})" if info['club_city'] else ''}</p>
                <p style="margin: 4px 0;"><strong>Date :</strong> {info['date_str']}</p>
                <p style="margin: 4px 0;"><strong>Heure :</strong> {info['time_str']}</p>
                <p style="margin: 4px 0;"><strong>Places occupées :</strong> {info['players_count']}/{info['max_players']}</p>
            </div>
            <p style="color: #6b7280; font-size: 14px;">Vous pouvez discuter avec les participants directement dans le chat du match sur l'application.</p>
            <p style="color: #6b7280; font-size: 14px;">L'équipe PadelUp</p>
        </div>
    </div>
    """

    return _send_email(organizer.email, subject, html_content)


def send_player_kicked_email(player, match, organizer=None):
    """Send notification email to a player who has been removed from a match"""
    info = _format_match_details(match)
    organizer_text = f" par l'organisateur ({organizer.username})" if organizer else ""
    subject = f'Information - Retrait du match {match.title}'

    html_content = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 24px;">
        <div style="background: #094A73; color: white; padding: 24px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">PadelUp</h1>
            <p style="margin: 8px 0 0; opacity: 0.9;">Information concernant votre match</p>
        </div>
        <div style="background: white; padding: 24px; border-radius: 0 0 16px 16px;">
            <p>Bonjour <strong>{player.first_name or player.username}</strong>,</p>
            <p>Vous avez été retiré du match <strong>"{match.title}"</strong>{organizer_text}.</p>
            <div style="background: #fef2f2; border: 1px solid #ef4444; border-radius: 12px; padding: 16px; margin: 16px 0;">
                <h3 style="margin: 0 0 12px; color: #991b1b;">{match.title}</h3>
                <p style="margin: 4px 0;"><strong>Club :</strong> {info['club_name']}{f" ({info['club_city']})" if info['club_city'] else ''}</p>
                <p style="margin: 4px 0;"><strong>Date :</strong> {info['date_str']}</p>
                <p style="margin: 4px 0;"><strong>Heure :</strong> {info['time_str']}</p>
            </div>
            <p style="color: #6b7280; font-size: 14px;">Vous pouvez explorer et rejoindre d'autres matchs disponibles dans l'application à tout moment.</p>
            <p style="color: #6b7280; font-size: 14px;">L'équipe PadelUp</p>
        </div>
    </div>
    """

    return _send_email(player.email, subject, html_content)


def send_match_cancelled_email(user, match):
    """Send notification email to participant when a match is cancelled"""
    info = _format_match_details(match)
    subject = f'Match annulé - {match.title}'

    html_content = f"""
    <div style="font-family: 'Inter', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #f8fafc; padding: 24px;">
        <div style="background: #094A73; color: white; padding: 24px; border-radius: 16px 16px 0 0; text-align: center;">
            <h1 style="margin: 0; font-size: 24px;">PadelUp</h1>
            <p style="margin: 8px 0 0; opacity: 0.9;">Annulation de match</p>
        </div>
        <div style="background: white; padding: 24px; border-radius: 0 0 16px 16px;">
            <p>Bonjour <strong>{user.first_name or user.username}</strong>,</p>
            <p>Le match <strong>"{match.title}"</strong> auquel vous participiez a été annulé par l'organisateur.</p>
            <div style="background: #fef2f2; border: 1px solid #ef4444; border-radius: 12px; padding: 16px; margin: 16px 0;">
                <h3 style="margin: 0 0 12px; color: #991b1b;">{match.title}</h3>
                <p style="margin: 4px 0;"><strong>Club :</strong> {info['club_name']}{f" ({info['club_city']})" if info['club_city'] else ''}</p>
                <p style="margin: 4px 0;"><strong>Date initiale :</strong> {info['date_str']}</p>
                <p style="margin: 4px 0;"><strong>Heure initiale :</strong> {info['time_str']}</p>
            </div>
            <p style="color: #6b7280; font-size: 14px;">N'hésitez pas à parcourir l'application pour trouver d'autres parties disponibles.</p>
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
