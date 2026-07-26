import logging
import re
from django.db import IntegrityError
from django.utils.translation import gettext as _
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

UNIQUE_CONSTRAINT_PATTERNS = [
    (r'court.*date.*start_time', "Ce terrain est déjà réservé pour la date et l'heure sélectionnées."),
    (r'match.*user', "Vous avez déjà rejoint ce match."),
    (r'match.*rater.*rated_user', "Vous avez déjà évalué ce joueur pour ce match."),
    (r'court.*match.*rater', "Vous avez déjà évalué ce terrain pour ce match."),
    (r'sender.*receiver', "Une demande d'ami a déjà été envoyée à cet utilisateur."),
    (r'user1.*user2', "Vous êtes déjà amis avec cet utilisateur."),
    (r'blocker.*blocked', "Cet utilisateur est déjà bloqué."),
    (r'user.*club', "Ce club est déjà enregistré dans vos favoris."),
]

def humanize_error_message(msg):
    """Transform raw DRF / Django / Database error strings into clean French messages."""
    if not isinstance(msg, str):
        msg = str(msg)

    msg_lower = msg.lower()

    for pattern, clean_msg in UNIQUE_CONSTRAINT_PATTERNS:
        if re.search(pattern, msg_lower):
            return clean_msg

    if "doivent former un ensemble unique" in msg_lower or "must make a unique set" in msg_lower:
        return "Cette réservation ou action existe déjà."

    if "this field is required" in msg_lower or "ce champ est obligatoire" in msg_lower:
        return "Certains champs obligatoires sont manquants."

    if "invalid pk" in msg_lower or "clé primaire non valide" in msg_lower or "does not exist" in msg_lower:
        return "L'élément spécifié est introuvable."

    return msg

def extract_first_error(data):
    """Recursively extract and humanize the first error message from DRF error structures."""
    if isinstance(data, str):
        return humanize_error_message(data)
    elif isinstance(data, list):
        if len(data) > 0:
            return extract_first_error(data[0])
        return "Erreur de validation."
    elif isinstance(data, dict):
        for key in ['detail', 'error', 'message', 'non_field_errors']:
            if key in data and data[key]:
                return extract_first_error(data[key])
        for key, val in data.items():
            if val:
                return extract_first_error(val)
    return str(data)

def custom_exception_handler(exc, context):
    """
    Custom exception handler to catch database/server/validation errors
    and return humanized French messages to the client.
    """
    response = exception_handler(exc, context)

    if response is not None:
        if response.status_code == 400:
            clean_message = extract_first_error(response.data)
            response.data = {'error': clean_message, 'detail': clean_message}
    else:
        if isinstance(exc, IntegrityError):
            logger.warning(f"Database IntegrityError: {exc}")
            clean_message = humanize_error_message(str(exc))
            if clean_message == str(exc):
                clean_message = "Cette réservation ou action a échoué car une entrée similaire existe déjà."
            return Response(
                {'error': clean_message, 'detail': clean_message},
                status=status.HTTP_400_BAD_REQUEST
            )

        logger.error(f"Unhandled server error: {exc}", exc_info=True)
        return Response(
            {'error': _("Une erreur interne du serveur est survenue. Veuillez réessayer plus tard."),
             'detail': _("Une erreur interne du serveur est survenue. Veuillez réessayer plus tard.")},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response
