import base64
import json
import logging
import os

logger = logging.getLogger(__name__)

# Top-level graceful imports for Firebase Admin SDK
try:
    import firebase_admin
    from firebase_admin import credentials, messaging
    HAS_FIREBASE = True
except ImportError:
    firebase_admin = None
    credentials = None
    messaging = None
    HAS_FIREBASE = False

_firebase_initialized = False


def get_firebase_app():
    """Lazily initialize Firebase Admin SDK using environment credentials"""
    global _firebase_initialized
    if _firebase_initialized:
        return True

    if not HAS_FIREBASE or firebase_admin is None or credentials is None:
        logger.warning(
            "firebase_admin library not available in environment. "
            "Push notifications disabled."
        )
        return False

    try:
        if firebase_admin._apps:
            _firebase_initialized = True
            return True

        cred_json_str = os.environ.get('FIREBASE_CREDENTIALS_JSON')
        cred_path = os.environ.get('FIREBASE_CREDENTIALS_PATH')

        cred_dict = None

        if cred_json_str:
            # Check if it was base64 encoded
            try:
                decoded = base64.b64decode(cred_json_str).decode('utf-8')
                cred_dict = json.loads(decoded)
            except Exception:
                cred_dict = json.loads(cred_json_str)

        elif cred_path and os.path.exists(cred_path):
            with open(cred_path, 'r', encoding='utf-8') as f:
                cred_dict = json.load(f)
        else:
            try:
                from django.conf import settings
                local_fcm_file = os.path.join(settings.BASE_DIR, 'firebase-service-account.json')
                if os.path.exists(local_fcm_file):
                    with open(local_fcm_file, 'r', encoding='utf-8') as f:
                        cred_dict = json.load(f)
            except Exception:
                pass

        if cred_dict:
            cred = credentials.Certificate(cred_dict)
            firebase_admin.initialize_app(cred)
            _firebase_initialized = True
            logger.info("Firebase Admin SDK successfully initialized.")
            return True
        else:
            logger.warning(
                "FIREBASE_CREDENTIALS_JSON not provided. "
                "Push notifications are disabled (in-app notifications will still be stored)."
            )
            return False

    except Exception as e:
        logger.error(f"Failed to initialize Firebase Admin SDK: {e}")
        return False


def send_push_notification(user, title, body, data=None, notification_type=None):
    """
    Send FCM push notification to all active devices of a user.
    Automatically removes invalid/unregistered device tokens.
    """
    if not get_firebase_app() or messaging is None:
        return 0

    from .models import DeviceToken

    tokens = list(DeviceToken.objects.filter(user=user).values_list('token', flat=True))
    if not tokens:
        logger.debug(f"No registered device tokens for user {user.username}")
        return 0

    # Ensure all data values are strings for FCM
    data_payload = {}
    if data:
        for k, v in data.items():
            data_payload[str(k)] = str(v) if v is not None else ''

    if notification_type:
        data_payload['type'] = str(notification_type)

    # Base notification
    notification = messaging.Notification(
        title=title,
        body=body,
    )

    # APNs config for iOS devices
    apns_config = messaging.APNSConfig(
        payload=messaging.APNSPayload(
            aps=messaging.Aps(
                alert=messaging.ApsAlert(title=title, body=body),
                badge=1,
                sound="default",
            ),
        ),
    )

    # Android config
    android_config = messaging.AndroidConfig(
        priority="high",
        notification=messaging.AndroidNotification(
            title=title,
            body=body,
            sound="default",
            channel_id="padelup_notifications",
        ),
    )

    multicast_msg = messaging.MulticastMessage(
        tokens=tokens,
        notification=notification,
        data=data_payload,
        apns=apns_config,
        android=android_config,
    )

    try:
        response = messaging.send_each_for_multicast(multicast_msg)
        logger.info(
            f"FCM Multicast sent to {user.username}: "
            f"{response.success_count} success, {response.failure_count} failed."
        )

        # Cleanup expired or invalid tokens
        if response.failure_count > 0:
            tokens_to_delete = []
            for idx, resp in enumerate(response.responses):
                if not resp.success:
                    err = resp.exception
                    err_code = getattr(err, 'code', None)
                    # Common codes for dead tokens
                    if err_code in ('registration-token-not-registered', 'invalid-argument') or \
                       'not registered' in str(err).lower():
                        tokens_to_delete.append(tokens[idx])

            if tokens_to_delete:
                DeviceToken.objects.filter(token__in=tokens_to_delete).delete()
                logger.info(f"Cleaned up {len(tokens_to_delete)} invalid device tokens.")

        return response.success_count

    except Exception as e:
        logger.error(f"Error sending FCM multicast to {user.username}: {e}")
        return 0


def create_notification(
    user,
    notification_type,
    message,
    match=None,
    friend_request=None,
    club=None,
    target='mobile',
    title="PadelUp",
    data=None,
):
    """
    Central helper to:
    1. Create and save a Notification row in the database.
    2. Dispatch an FCM push notification if targeting mobile or both.
    Never raises an exception so calling views remain safe.
    """
    from .models import Notification

    try:
        notification_obj = Notification.objects.create(
            user=user,
            type=notification_type,
            message=message,
            match=match,
            friend_request=friend_request,
            club=club,
            target=target,
        )

        # If targeting mobile, dispatch push notification
        if target in ('mobile', 'both'):
            push_data = dict(data or {})
            push_data['notification_id'] = str(notification_obj.id)
            if match:
                push_data['match_id'] = str(match.id)
            if friend_request:
                push_data['friend_request_id'] = str(friend_request.id)
            if club:
                push_data['club_id'] = str(club.id)

            send_push_notification(
                user=user,
                title=title,
                body=message,
                data=push_data,
                notification_type=notification_type,
            )

        return notification_obj
    except Exception as e:
        logger.error(f"Failed to create notification for {user.username}: {e}")
        return None
