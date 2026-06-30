import logging
from django.db import IntegrityError
from django.utils.translation import gettext as _
from rest_framework.views import exception_handler
from rest_framework.response import Response
from rest_framework import status

logger = logging.getLogger(__name__)

def custom_exception_handler(exc, context):
    """
    Custom exception handler to catch database/server errors
    and return humanized French messages to the client.
    """
    # Call REST framework's default exception handler first to get the standard error response.
    response = exception_handler(exc, context)

    if response is not None:
        # For standard DRF responses, if they have an 'error' or 'detail' key, we can translate standard ones.
        # But we'll mostly rely on default Django/DRF translation for built-in validation messages (LANGUAGE_CODE = 'fr').
        pass
    else:
        # Handle database integrity errors (unique constraints, foreign key failures, null constraints)
        if isinstance(exc, IntegrityError):
            logger.warning(f"Database IntegrityError: {exc}")
            # Humanized French message for duplicate key or other constraint violations
            return Response(
                {'detail': _("Cette information existe déjà dans notre système (ex: email ou nom d'utilisateur déjà pris).")},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Log unhandled exceptions (500 Server Errors) with traceback for developers
        logger.error(f"Unhandled server error: {exc}", exc_info=True)
        
        # Return a safe, clean, user-friendly French message
        return Response(
            {'detail': _("Une erreur interne du serveur est survenue. Veuillez réessayer plus tard.")},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

    return response
