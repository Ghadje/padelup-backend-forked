import base64
import logging
import traceback
import requests as http_requests

from django.contrib.auth import authenticate, login, logout

logger = logging.getLogger(__name__)
from django.contrib.auth.models import User
from django.shortcuts import get_object_or_404
from django.db import models
from django.db.models import Q, Avg, Count, Case, When, IntegerField, Value
from django.db.models.functions import Concat
from django.utils import timezone
from datetime import datetime, timedelta

FREEIMAGE_API_KEY = '6d207e02198a847aa98d0a2a901485a5'


def _upload_image_to_freeimage(uploaded_file):
    """Upload an image file to Freeimage.host and return its URL, or None on failure."""
    try:
        file_content = uploaded_file.read()
        b64_image = base64.b64encode(file_content).decode('utf-8')
        resp = http_requests.post(
            'https://freeimage.host/api/1/upload',
            data={
                'key': FREEIMAGE_API_KEY,
                'action': 'upload',
                'source': b64_image,
                'format': 'json',
            },
            timeout=30,
        )
        if resp.status_code == 200:
            resp_data = resp.json()
            if resp_data.get('status_code') == 200:
                return resp_data['image']['url']
            logger.warning(f"Freeimage upload rejected: {resp_data}")
        else:
            logger.warning(f"Freeimage upload non-200: {resp.status_code} {resp.text[:200]}")
    except Exception as e:
        logger.warning(f"Freeimage upload failed: {e}")
    return None

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.authtoken.models import Token
from rest_framework.pagination import PageNumberPagination


def is_admin_user(user):
    """
    Check if user has full administrative privileges.
    A user is an admin if they are a superuser, staff member, or have profile.role == 'admin'.
    """
    if not user or not user.is_authenticated:
        return False
    if user.is_superuser or user.is_staff:
        return True
    try:
        return getattr(user, 'profile', None) and user.profile.role in ['admin', 'superadmin']
    except Exception:
        return False


def is_manager_or_admin(user):
    """
    Check if user is a manager or admin.
    """
    if not user or not user.is_authenticated:
        return False
    if is_admin_user(user):
        return True
    try:
        return getattr(user, 'profile', None) and user.profile.role in ['admin', 'manager']
    except Exception:
        return False


class IsAdminUserRole(permissions.BasePermission):
    """
    Allows access only to admin users (superusers, staff, or profile.role == 'admin').
    """
    def has_permission(self, request, view):
        return is_admin_user(request.user)


class IsManagerUserRole(permissions.BasePermission):
    """
    Allows access only to managers or admins.
    """
    def has_permission(self, request, view):
        return is_manager_or_admin(request.user)


import random

from .models import (
    Profile, PlayerStats, Club, Court, Booking, Match, MatchParticipant,
    MatchMessage, MatchComment, Rating, CourtRating, Notification, DeviceToken, CommunityPost,
    PostReply, CommunityGroup, FriendRequest, Friendship, PrivateMessage,
    BlockedUser, PasswordResetCode, PasswordChangeAttempt, EmailVerificationCode
)
from .fcm_service import (
    create_notification, send_push_notification,
    get_user_display_name, get_match_members
)
from .email_service import (

    send_welcome_email, send_password_reset_email, send_verification_email,
    send_match_creation_confirmation, send_match_join_confirmation,
    send_player_joined_organizer_email, send_player_kicked_email,
    send_match_cancelled_email,
)
from .serializers import (
    UserSerializer, ProfileSerializer, ProfileSetupSerializer, ProfileUpdateSerializer,
    PlayerStatsSerializer, ClubSerializer, CourtSerializer, BookingSerializer,
    MatchSerializer, MatchDetailSerializer, MatchParticipantSerializer,
    MatchMessageSerializer, MatchCommentSerializer, AdminCommentSerializer, RatingSerializer, CourtRatingSerializer,
    NotificationSerializer, CommunityPostSerializer, PostReplySerializer,
    CommunityGroupSerializer, FriendRequestSerializer, FriendshipSerializer,
    PrivateMessageSerializer, BlockedUserSerializer, RegisterSerializer,
    LoginSerializer, UserDetailSerializer
)


# ============================================================================
# AUTHENTICATION APIs
# ============================================================================

class RegisterView(APIView):
    """User registration API"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()

            # Invalidate any previous unused verification codes for this user
            EmailVerificationCode.objects.filter(user=user, is_used=False).update(is_used=True)

            # Generate 6-digit code
            code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
            EmailVerificationCode.objects.create(user=user, code=code)

            # Send verification email (non-blocking)
            try:
                send_verification_email(user, code)
            except Exception as e:
                logger.error(f"Failed to send verification email: {e}")

            # Return verification required response
            return Response({
                'verification_required': True,
                'email': user.email,
                'message': 'Un code de confirmation a été envoyé à votre e-mail.'
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class RegisterVerifyView(APIView):
    """Verify registration code and activate user"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        code = request.data.get('code', '').strip()

        if not email or not code:
            return Response({'error': 'Email et code requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        # Retrieve the latest unused verification code within the last 24 hours
        verification_code = EmailVerificationCode.objects.filter(
            user=user,
            code=code,
            is_used=False,
            created_at__gte=timezone.now() - timedelta(hours=24)
        ).first()

        if not verification_code:
            return Response({'error': 'Code de confirmation invalide ou expiré'}, status=status.HTTP_400_BAD_REQUEST)

        # Activate user
        user.is_active = True
        user.save()

        # Mark code as used
        verification_code.is_used = True
        verification_code.save()

        # Send welcome email (moved here after verification)
        try:
            send_welcome_email(user)
        except Exception as e:
            logger.error(f"Failed to send welcome email: {e}")

        # Create/Get auth token
        token, created = Token.objects.get_or_create(user=user)

        return Response({
            'user': UserSerializer(user).data,
            'profile': ProfileSerializer(user.profile).data if hasattr(user, 'profile') else None,
            'token': token.key,
            'message': 'Inscription validée avec succès'
        }, status=status.HTTP_200_OK)


class RegisterResendCodeView(APIView):
    """Resend registration confirmation code"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response({'error': 'Email requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Only resend code for inactive users
            user = User.objects.get(email__iexact=email)
            if user.is_active:
                return Response({'error': 'Ce compte est déjà activé'}, status=status.HTTP_400_BAD_REQUEST)
        except User.DoesNotExist:
            # Security: return success even if email doesn't exist, to not leak emails
            return Response({'message': 'Un code de confirmation a été envoyé à votre e-mail.'})

        # Invalidate previous codes
        EmailVerificationCode.objects.filter(user=user, is_used=False).update(is_used=True)

        # Generate new 6-digit code
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        EmailVerificationCode.objects.create(user=user, code=code)

        # Send code
        try:
            send_verification_email(user, code)
        except Exception as e:
            logger.error(f"Failed to resend verification email: {e}")

        return Response({'message': 'Un code de confirmation a été envoyé à votre e-mail.'})


class LoginView(APIView):
    """User login API"""
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            username = serializer.validated_data.get('username')
            password = serializer.validated_data.get('password')

            identifier = (username or email or '').strip()
            user = None
            user_obj = None

            if identifier:
                # 1. Search for matching user by email or username (case-insensitive)
                try:
                    user_obj = User.objects.filter(
                        Q(username__iexact=identifier) | Q(email__iexact=identifier)
                    ).first()
                    if user_obj:
                        user = authenticate(username=user_obj.username, password=password)
                except Exception:
                    pass

                # 2. Direct authenticate fallback
                if not user:
                    user = authenticate(username=identifier, password=password)

            if user:
                if not user.is_active:
                    return Response({'error': 'Ce compte est désactivé.'}, status=status.HTTP_401_UNAUTHORIZED)
                login(request, user)
                token, created = Token.objects.get_or_create(user=user)
                return Response({
                    'user': UserSerializer(user).data,
                    'profile': ProfileSerializer(user.profile).data if hasattr(user, 'profile') else None,
                    'token': token.key,
                    'message': 'Connexion réussie'
                }, status=status.HTTP_200_OK)

            # Detailed error explanation
            if user_obj:
                return Response({'error': 'Mot de passe incorrect.'}, status=status.HTTP_401_UNAUTHORIZED)
            else:
                return Response({'error': "Aucun compte n'est associé à cet e-mail ou nom d'utilisateur."}, status=status.HTTP_401_UNAUTHORIZED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleLoginView(APIView):
    """Google Sign-In API"""
    permission_classes = [AllowAny]

    def post(self, request):
        id_token = request.data.get('id_token')
        if not id_token:
            return Response({'error': 'id_token requis'}, status=status.HTTP_400_BAD_REQUEST)

        # Verify token with Google's tokeninfo endpoint
        try:
            resp = http_requests.get(
                f'https://oauth2.googleapis.com/tokeninfo?id_token={id_token}',
                timeout=10
            )
            if resp.status_code != 200:
                return Response({'error': 'Token Google invalide'}, status=status.HTTP_400_BAD_REQUEST)

            payload = resp.json()
            email = payload.get('email')
            given_name = payload.get('given_name', '')
            family_name = payload.get('family_name', '')
            picture = payload.get('picture', '')

            if not email:
                return Response({'error': 'Pas d\'email associé à ce compte Google'}, status=status.HTTP_400_BAD_REQUEST)

            # Find or create user
            is_new_user = False
            user = User.objects.filter(email__iexact=email).first()
            if not user:
                is_new_user = True
                
                # Generate unique friendly username from email prefix
                base_username = email.split('@')[0]
                import re
                base_username = re.sub(r'[^a-zA-Z0-9_.-]', '', base_username)
                username = base_username
                
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1

                password = User.objects.make_random_password()
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    password=password,
                    first_name=given_name,
                    last_name=family_name
                )
                user.is_active = True # Google login is auto-verified
                user.save()
            else:
                if not user.is_active:
                    user.is_active = True
                    user.save()

            # Ensure profile exists
            profile, profile_created = Profile.objects.get_or_create(user=user)
            
            # If profile was newly created, or if full_name is empty, populate it
            full_name = f"{given_name} {family_name}".strip() or payload.get('name', '')
            if profile_created or not profile.full_name:
                profile.full_name = full_name
                profile.save(update_fields=['full_name'])

            if profile_created or not profile.external_avatar_url:
                if picture:
                    profile.external_avatar_url = picture
                    profile.save(update_fields=['external_avatar_url'])

            # Ensure player stats exists
            PlayerStats.objects.get_or_create(user=user)

            # Generate/Get Token
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                'user': UserSerializer(user).data,
                'profile': ProfileSerializer(profile).data,
                'token': token.key,
                'is_new_user': is_new_user,
                'message': 'Connexion Google réussie'
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Google Login error: {e}\n{traceback.format_exc()}")
            return Response({'error': f'Erreur de connexion Google: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AppleLoginView(APIView):
    """Sign in with Apple API"""
    permission_classes = [AllowAny]

    def post(self, request):
        identity_token = request.data.get('identity_token')
        if not identity_token:
            return Response({'error': 'identity_token requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            import os
            import re
            import jwt
            from jwt import PyJWKClient

            # Verify Apple JWT using Apple's JWKS
            jwks_client = PyJWKClient("https://appleid.apple.com/auth/keys")
            signing_key = jwks_client.get_signing_key_from_jwt(identity_token)

            allowed_audiences = [
                a.strip() for a in os.environ.get(
                    'APPLE_CLIENT_ID',
                    'com.padelup.padelup-new,com.padelup.padelUp'
                ).split(',') if a.strip()
            ]

            payload = jwt.decode(
                identity_token,
                signing_key.key,
                algorithms=["RS256"],
                audience=allowed_audiences,
                issuer="https://appleid.apple.com",
                options={"verify_exp": True},
            )

            apple_sub = payload.get('sub')
            token_email = payload.get('email')
            email = token_email or request.data.get('email')
            given_name = request.data.get('first_name') or ''
            family_name = request.data.get('last_name') or ''

            if not apple_sub:
                return Response({'error': 'Token Apple invalide: identifiant utilisateur manquant'}, status=status.HTTP_400_BAD_REQUEST)

            # Find or create user
            is_new_user = False
            user = None
            if email:
                user = User.objects.filter(email__iexact=email).first()

            if not user and apple_sub:
                user = User.objects.filter(username=f"apple_{apple_sub[:20]}").first()

            if not user:
                is_new_user = True

                # Generate unique friendly username from email prefix or apple_sub
                if email:
                    base_username = email.split('@')[0]
                else:
                    base_username = f"apple_{apple_sub[:8]}"

                base_username = re.sub(r'[^a-zA-Z0-9_.-]', '', base_username)
                username = base_username

                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}_{counter}"
                    counter += 1

                user_email = email if email else f"{username}@privaterelay.appleid.com"
                password = User.objects.make_random_password()
                user = User.objects.create_user(
                    username=username,
                    email=user_email,
                    password=password,
                    first_name=given_name,
                    last_name=family_name
                )
                user.is_active = True  # Apple login is auto-verified
                user.save()
            else:
                if not user.is_active:
                    user.is_active = True
                    user.save()

            # Ensure profile exists
            profile, profile_created = Profile.objects.get_or_create(user=user)

            # If profile was newly created, or if full_name is empty, populate it
            full_name = f"{given_name} {family_name}".strip()
            if full_name and (profile_created or not profile.full_name):
                profile.full_name = full_name
                profile.save(update_fields=['full_name'])

            # Ensure player stats exists
            PlayerStats.objects.get_or_create(user=user)

            # Generate/Get Token
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                'user': UserSerializer(user).data,
                'profile': ProfileSerializer(profile).data,
                'token': token.key,
                'is_new_user': is_new_user,
                'message': 'Connexion Apple réussie'
            }, status=status.HTTP_200_OK)

        except jwt.PyJWTError as e:
            logger.error(f"Apple JWT verification failed: {e}\n{traceback.format_exc()}")
            return Response({'error': f'Jeton Apple invalide ou expiré: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"Apple Login error: {e}\n{traceback.format_exc()}")
            return Response({'error': f'Erreur de connexion Apple: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class LogoutView(APIView):
    """User logout API"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Delete auth token
        try:
            request.user.auth_token.delete()
        except:
            pass
        logout(request)
        return Response({'message': 'Déconnexion réussie'}, status=status.HTTP_200_OK)


class PasswordResetRequestView(APIView):
    """Request a password reset code (limited to 3 emails/day)"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        if not email:
            return Response({'detail': 'Email requis', 'error': 'Email requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            # Return success even if email doesn't exist (security: don't reveal accounts)
            return Response({'message': 'Si un compte existe avec cet email, un code a été envoyé.'})

        # Rate limit: maximum 3 password reset emails in 24 hours
        one_day_ago = timezone.now() - timedelta(hours=24)
        recent_requests = PasswordResetCode.objects.filter(
            user=user,
            created_at__gte=one_day_ago
        ).count()

        if recent_requests >= 3:
            return Response(
                {
                    'error': 'Vous avez atteint le nombre maximum de tentatives de réinitialisation de mot de passe (3 par jour). Veuillez réessayer demain.',
                    'detail': 'Vous avez atteint le nombre maximum de tentatives de réinitialisation de mot de passe (3 par jour). Veuillez réessayer demain.',
                    'message': 'Vous avez atteint le nombre maximum de tentatives de réinitialisation de mot de passe (3 par jour). Veuillez réessayer demain.',
                    'attempts_exceeded': True,
                    'remaining_attempts': 0
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        # Invalidate previous codes
        PasswordResetCode.objects.filter(user=user, is_used=False).update(is_used=True)

        # Generate 6-digit code
        code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
        PasswordResetCode.objects.create(user=user, code=code)

        # Send email
        try:
            send_password_reset_email(user, code)
        except Exception as e:
            print(f'Failed to send password reset email: {e}')

        remaining = max(0, 3 - (recent_requests + 1))
        return Response({
            'message': 'Si un compte existe avec cet email, un code a été envoyé.',
            'remaining_attempts': remaining
        })


class PasswordResetConfirmView(APIView):
    """Confirm password reset with code"""
    permission_classes = [AllowAny]

    def post(self, request):
        email = request.data.get('email', '').strip()
        code = request.data.get('code', '').strip()
        new_password = request.data.get('new_password', '')

        if not email or not code or not new_password:
            return Response({'detail': 'Email, code et nouveau mot de passe requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({'detail': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        if len(new_password) < 8:
            return Response({'detail': 'Le mot de passe doit contenir au moins 8 caractères'}, status=status.HTTP_400_BAD_REQUEST)

        reset_code = PasswordResetCode.objects.filter(
            user=user, 
            code=code, 
            is_used=False,
            created_at__gte=timezone.now() - timedelta(hours=1)
        ).first()

        if not reset_code:
            return Response({'detail': 'Code invalide ou expiré'}, status=status.HTTP_400_BAD_REQUEST)

        # Reset password
        user.set_password(new_password)
        user.save()

        # Mark code as used
        reset_code.is_used = True
        reset_code.save()

        return Response({'message': 'Mot de passe réinitialisé avec succès'}, status=status.HTTP_200_OK)


class ChangePasswordView(APIView):
    """Change password for authenticated user (limited to 3 attempts/day)"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Rate limit: maximum 3 password changes/attempts in 24 hours
        one_day_ago = timezone.now() - timedelta(hours=24)
        recent_changes = PasswordChangeAttempt.objects.filter(
            user=user,
            created_at__gte=one_day_ago
        ).count()

        if recent_changes >= 3:
            return Response(
                {
                    'error': 'Vous avez atteint le nombre maximum de tentatives de modification de mot de passe (3 par jour). Veuillez réessayer demain.',
                    'detail': 'Vous avez atteint le nombre maximum de tentatives de modification de mot de passe (3 par jour). Veuillez réessayer demain.',
                    'message': 'Vous avez atteint le nombre maximum de tentatives de modification de mot de passe (3 par jour). Veuillez réessayer demain.',
                    'attempts_exceeded': True,
                    'remaining_attempts': 0
                },
                status=status.HTTP_429_TOO_MANY_REQUESTS
            )

        old_password = request.data.get('old_password')
        new_password = request.data.get('new_password')

        if not old_password or not new_password:
            return Response({'error': 'Ancien et nouveau mot de passe requis'}, status=status.HTTP_400_BAD_REQUEST)

        if not user.check_password(old_password):
            return Response({'error': 'L\'ancien mot de passe est incorrect'}, status=status.HTTP_400_BAD_REQUEST)

        if len(new_password) < 8:
            return Response({'error': 'Le nouveau mot de passe doit contenir au moins 8 caractères'}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()

        # Record password change
        PasswordChangeAttempt.objects.create(user=user, success=True)

        remaining = max(0, 3 - (recent_changes + 1))
        return Response({
            'message': 'Mot de passe changé avec succès',
            'remaining_attempts': remaining
        }, status=status.HTTP_200_OK)


class ProfileSetupView(APIView):
    """Profile setup after registration"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            profile = request.user.profile

            data = {
                key: request.data.get(key)
                for key in ('location', 'bio', 'skill_level', 'evaluation_type')
                if key in request.data
            }
            if 'right_handed' in request.data:
                data['right_handed'] = request.data.get('right_handed')
            elif 'right-handed' in request.data:
                data['right_handed'] = request.data.get('right-handed')

            # Upload avatar to Freeimage.host if provided
            if 'avatar' in request.FILES:
                uploaded_file = request.FILES['avatar']
                try:
                    file_content = uploaded_file.read()
                    b64_image = base64.b64encode(file_content).decode('utf-8')
                    resp = http_requests.post(
                        'https://freeimage.host/api/1/upload',
                        data={
                            'key': FREEIMAGE_API_KEY,
                            'action': 'upload',
                            'source': b64_image,
                            'format': 'json',
                        },
                        timeout=30,
                    )
                    if resp.status_code == 200:
                        resp_data = resp.json()
                        if resp_data.get('status_code') == 200:
                            profile.external_avatar_url = resp_data['image']['url']
                            profile.save(update_fields=['external_avatar_url'])
                    else:
                        logger.warning(f"Freeimage upload non-200: {resp.status_code} {resp.text[:200]}")
                except Exception as e:
                    logger.warning(f"Freeimage upload failed: {e}")

            serializer = ProfileSetupSerializer(profile, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response({
                    'profile': ProfileSerializer(profile).data,
                    'message': 'Configuration du profil terminée'
                }, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            logger.error(f"ProfileSetupView error: {e}\n{traceback.format_exc()}")
            return Response(
                {'detail': f'Server error: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ============================================================================
# USER PROFILE APIs
# ============================================================================

class ProfileView(APIView):
    """User profile API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get current user's profile"""
        user = request.user
        serializer = UserDetailSerializer(user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        """Update current user's profile"""
        profile = request.user.profile

        # Build a plain dict of form fields (exclude file — handled separately
        # to avoid deep-copy of disk-backed uploads)
        allowed_fields = (
            'phone_number', 'full_name', 'bio', 'location',
            'skill_level', 'evaluation_type', 'external_avatar_url',
            'user_first_name', 'user_last_name', 'user_email',
            'right_handed', 'is_completed',
        )
        data = {key: request.data.get(key) for key in allowed_fields if key in request.data}
        if 'right-handed' in request.data:
            data['right_handed'] = request.data.get('right-handed')

        # Auto-mark profile as completed when skill_level is updated
        if 'skill_level' in request.data and request.data.get('skill_level') is not None:
            data['is_completed'] = True

        # Handle avatar_url (e.g. DiceBear URL) sent as a text field
        avatar_url = request.data.get('avatar_url') or request.data.get('external_avatar_url')
        if isinstance(avatar_url, list):
            avatar_url = avatar_url[0] if avatar_url else None
        if avatar_url and isinstance(avatar_url, str):
            import urllib.parse
            data['external_avatar_url'] = urllib.parse.quote(avatar_url.strip(), safe=':/?#[]@!$&\'()*+,;=')

        # Upload file avatar to Freeimage.host and store URL
        if 'avatar' in request.FILES:
            uploaded_file = request.FILES['avatar']
            try:
                file_content = uploaded_file.read()
                b64_image = base64.b64encode(file_content).decode('utf-8')
                resp = http_requests.post(
                    'https://freeimage.host/api/1/upload',
                    data={
                        'key': FREEIMAGE_API_KEY,
                        'action': 'upload',
                        'source': b64_image,
                        'format': 'json',
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    resp_data = resp.json()
                    if resp_data.get('status_code') == 200:
                        image_url = resp_data['image']['url']
                        data['external_avatar_url'] = image_url
                        # Clear old local avatar field
                        profile.avatar = None
                        profile.save(update_fields=['avatar'])
                    else:
                        return Response(
                            {'detail': 'Échec du téléchargement de l\'image'},
                            status=status.HTTP_400_BAD_REQUEST
                        )
                else:
                    return Response(
                        {'detail': 'Service d\'hébergement d\'images indisponible'},
                        status=status.HTTP_502_BAD_GATEWAY
                    )
            except Exception as e:
                return Response(
                    {'detail': f'Image upload error: {str(e)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )

        serializer = ProfileUpdateSerializer(profile, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'profile': ProfileSerializer(profile, context={'request': request}).data,
                'message': 'Profil mis à jour avec succès'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """Delete user account and all associated data"""
        user = request.user

        # Delete auth token
        try:
            user.auth_token.delete()
        except:
            pass

        # Django will cascade delete all related data (matches, bookings, ratings, etc.)
        # due to foreign key relationships
        user.delete()

        return Response({'message': 'Compte supprimé avec succès'}, status=status.HTTP_200_OK)


class PublicProfileView(APIView):
    """View other user's public profile"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)

            # Check if blocked
            if BlockedUser.is_blocked(request.user, user):
                return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)

            # Build response
            data = {
                'user': UserSerializer(user).data,
                'profile': ProfileSerializer(user.profile, context={'request': request}).data if hasattr(user, 'profile') else None,
                'stats': PlayerStatsSerializer(user.stats).data if hasattr(user, 'stats') else None,
                'is_friend': Friendship.are_friends(request.user, user),
                'is_blocked': False,
                'is_own_profile': user.id == request.user.id
            }

            # Add friend request status if applicable
            friend_request = FriendRequest.objects.filter(
                Q(sender=request.user, receiver=user) |
                Q(sender=user, receiver=request.user),
                status='pending'
            ).first()

            if friend_request:
                data['friend_request'] = FriendRequestSerializer(friend_request).data

            return Response(data, status=status.HTTP_200_OK)

        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# CLUB APIs
# ============================================================================

class ClubListView(APIView):
    """List and search clubs"""
    permission_classes = [AllowAny]  # Allow public access to clubs

    def get(self, request):
        # Get query parameters
        search = request.query_params.get('search', '')
        city = request.query_params.get('city', '')
        is_partner = request.query_params.get('is_partner', '')
        min_rating = request.query_params.get('min_rating', '')
        lat = request.query_params.get('lat', '')
        lng = request.query_params.get('lng', '')
        max_distance = request.query_params.get('max_distance', '')

        # Base queryset
        clubs = Club.objects.all()

        # If user is a manager (and not an admin), only show clubs they manage
        if request.user.is_authenticated and not is_admin_user(request.user):
            try:
                profile = request.user.profile
                if profile.role == 'manager':
                    clubs = clubs.filter(manager=request.user)
            except Exception:
                pass

        # Apply filters
        if search:
            search_str = search.strip()
            exact_matches = clubs.filter(
                Q(name__icontains=search_str) |
                Q(address__icontains=search_str) |
                Q(city__icontains=search_str)
            )
            if exact_matches.exists():
                clubs = exact_matches
            else:
                import difflib
                search_lower = search_str.lower()
                matched_ids = []
                for c in clubs:
                    full_text = f"{c.name} {c.city or ''} {c.address or ''}".lower()
                    words = full_text.split()
                    matched = False
                    for w in words:
                        if search_lower in w or w in search_lower:
                            matched = True
                            break
                        if len(search_lower) >= 3 and len(w) >= 3:
                            ratio = difflib.SequenceMatcher(None, search_lower, w).ratio()
                            if ratio >= 0.65:
                                matched = True
                                break
                    if not matched:
                        ratio = difflib.SequenceMatcher(None, search_lower, c.name.lower()).ratio()
                        if ratio >= 0.6:
                            matched = True
                    if matched:
                        matched_ids.append(c.id)
                clubs = clubs.filter(id__in=matched_ids)

        if city:
            clubs = clubs.filter(city__icontains=city)

        if is_partner:
            clubs = clubs.filter(is_partner=is_partner.lower() == 'true')

        if min_rating:
            clubs = clubs.filter(rating__gte=float(min_rating))

        # Bounding box filter (for map viewport exploration)
        min_lat = request.query_params.get('min_lat')
        max_lat = request.query_params.get('max_lat')
        min_lng = request.query_params.get('min_lng')
        max_lng = request.query_params.get('max_lng')
        if min_lat and max_lat and min_lng and max_lng:
            try:
                clubs = clubs.filter(
                    latitude__gte=float(min_lat),
                    latitude__lte=float(max_lat),
                    longitude__gte=float(min_lng),
                    longitude__lte=float(max_lng)
                )
            except (ValueError, TypeError):
                pass

        # Sort by distance if coordinates provided
        if lat and lng:
            try:
                from math import radians, cos, sin, asin, sqrt

                def haversine_distance(lat1, lon1, lat2, lon2):
                    """Calculate the great circle distance between two points on Earth"""
                    # Convert decimal degrees to radians
                    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])

                    # Haversine formula
                    dlat = lat2 - lat1
                    dlon = lon2 - lon1
                    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
                    c = 2 * asin(sqrt(a))
                    # Radius of Earth in kilometers
                    r = 6371
                    return c * r

                user_lat = float(lat)
                user_lng = float(lng)

                # Calculate distance for each club
                clubs_with_distance = []
                for club in clubs:
                    distance = haversine_distance(
                        user_lat, user_lng,
                        float(club.latitude), float(club.longitude)
                    )
                    clubs_with_distance.append((club, distance))

                # Sort by distance
                clubs_with_distance.sort(key=lambda x: x[1])

                # Filter by max_distance if provided
                if max_distance:
                    max_dist = float(max_distance)
                    clubs_with_distance = [(c, d) for c, d in clubs_with_distance if d <= max_dist]

                # Extract clubs and add distance to each
                clubs = [club for club, _ in clubs_with_distance]
                for club, distance in clubs_with_distance:
                    club.distance = round(distance, 2)

            except (ValueError, TypeError) as e:
                # If there's an error with coordinates, just continue without filtering
                pass

        # Paginate
        page_size_param = request.query_params.get('page_size', 20)
        try:
            page_size = min(int(page_size_param), 100)
        except (ValueError, TypeError):
            page_size = 20

        paginator = PageNumberPagination()
        paginator.page_size = page_size
        result_page = paginator.paginate_queryset(clubs, request)

        serializer = ClubSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """Create a new club (admin/manager dashboard)"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentification requise'}, status=status.HTTP_401_UNAUTHORIZED)
            
        if not is_manager_or_admin(request.user):
            return Response({'error': 'Seuls les administrateurs et managers peuvent créer des clubs'}, status=status.HTTP_403_FORBIDDEN)

        # Build plain dict so we can modify it safely without deep-copying file uploads
        data = {k: v for k, v in request.data.items() if k != 'primary_photo'}
        
        # If user is a manager (and not an admin), force them as the manager of the new club
        if not is_admin_user(request.user):
            data['manager'] = request.user.id

        serializer = ClubSerializer(data=data)
        if serializer.is_valid():
            club = serializer.save()
            # Handle optional primary_photo upload to Freeimage
            if 'primary_photo' in request.FILES:
                url = _upload_image_to_freeimage(request.FILES['primary_photo'])
                if url:
                    club.images = [url] + (club.images or [])
                    club.save(update_fields=['images'])
            return Response(ClubSerializer(club, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def check_club_manager_permission(user, club):
    """Check if user has permission to manage a club"""
    if not user.is_authenticated:
        return False
    if is_admin_user(user):
        return True
    try:
        profile = user.profile
        if profile.role == 'manager' and club.manager == user:
            return True
    except Exception:
        pass
    return False


class ClubDetailView(APIView):
    """Club detail API"""
    permission_classes = [AllowAny]  # Allow access for admin dashboard

    def get(self, request, club_id):
        """Get club details"""
        try:
            club = Club.objects.get(id=club_id)
            serializer = ClubSerializer(club, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Club.DoesNotExist:
            return Response({'error': 'Club non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, club_id):
        """Update club (admin/manager dashboard)"""
        try:
            club = Club.objects.get(id=club_id)
            if not check_club_manager_permission(request.user, club):
                return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)
        except Club.DoesNotExist:
            return Response({'error': 'Club non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        data = {k: v for k, v in request.data.items() if k != 'primary_photo'}
        serializer = ClubSerializer(club, data=data, partial=True)
        if serializer.is_valid():
            serializer.save()
            if 'primary_photo' in request.FILES:
                url = _upload_image_to_freeimage(request.FILES['primary_photo'])
                if url:
                    club.images = [url] + [u for u in (club.images or []) if u != url]
                    club.save(update_fields=['images'])
            return Response(ClubSerializer(club, context={'request': request}).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, club_id):
        """Patch club (for image uploads from admin/manager dashboard)"""
        try:
            club = Club.objects.get(id=club_id)
            if not check_club_manager_permission(request.user, club):
                return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)
        except Club.DoesNotExist:
            return Response({'error': 'Club non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        if 'primary_photo' in request.FILES:
            url = _upload_image_to_freeimage(request.FILES['primary_photo'])
            if not url:
                return Response(
                    {'detail': 'Échec du téléchargement de l\'image sur le service d\'hébergement'},
                    status=status.HTTP_502_BAD_GATEWAY
                )
            club.images = [url] + [u for u in (club.images or []) if u != url]
            club.save(update_fields=['images'])

        data = {k: v for k, v in request.data.items() if k != 'primary_photo'}
        if data:
            serializer = ClubSerializer(club, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            ClubSerializer(club, context={'request': request}).data,
            status=status.HTTP_200_OK
        )

    def delete(self, request, club_id):
        """Delete club (admin only)"""
        # Managers usually shouldn't delete clubs, only Admins
        try:
            club = Club.objects.get(id=club_id)
            if not is_admin_user(request.user):
                return Response({'error': 'Seuls les administrateurs peuvent supprimer des clubs'}, status=status.HTTP_403_FORBIDDEN)

            club.delete()
            return Response({'message': 'Club supprimé avec succès'}, status=status.HTTP_204_NO_CONTENT)
        except Club.DoesNotExist:
            return Response({'error': 'Club non trouvé'}, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# COURT APIs
# ============================================================================

class CourtListView(APIView):
    """List courts by club"""
    permission_classes = [AllowAny]  # Allow access for admin dashboard

    def get(self, request, club_id):
        """Get all courts for a club"""
        try:
            club = Club.objects.get(id=club_id)

            # Check manager permission
            if request.user.is_authenticated and not is_admin_user(request.user):
                try:
                    profile = request.user.profile
                    if profile.role == 'manager':
                        if club.manager != request.user:
                             return Response({'error': 'Vous ne gérez pas ce club'}, status=status.HTTP_403_FORBIDDEN)
                except Exception:
                    pass

            courts = Court.objects.filter(club=club)
            serializer = CourtSerializer(courts, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Club.DoesNotExist:
            return Response({'error': 'Club non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, club_id):
        """Create a new court (admin/manager dashboard)"""
        try:
            club = Club.objects.get(id=club_id)
            if not check_club_manager_permission(request.user, club):
                return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = CourtSerializer(data=request.data)
            if serializer.is_valid():
                court = serializer.save(club=club)
                return Response(CourtSerializer(court).data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Club.DoesNotExist:
            return Response({'error': 'Club non trouvé'}, status=status.HTTP_404_NOT_FOUND)


class CourtDetailView(APIView):
    """Court detail API"""
    permission_classes = [AllowAny]  # Allow access for admin dashboard

    def get(self, request, court_id):
        """Get court details"""
        try:
            court = Court.objects.get(id=court_id)
            serializer = CourtSerializer(court)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Court.DoesNotExist:
            return Response({'error': 'Court non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, court_id):
        """Update court (admin/manager dashboard)"""
        try:
            court = Court.objects.get(id=court_id)
            if not check_club_manager_permission(request.user, court.club):
                return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)
            
            serializer = CourtSerializer(court, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Court.DoesNotExist:
            return Response({'error': 'Court non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, court_id):
        """Delete court (admin/manager dashboard)"""
        try:
            court = Court.objects.get(id=court_id)
            if not check_club_manager_permission(request.user, court.club):
                return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)
            
            court.delete()
            return Response({'message': 'Court supprimé avec succès'}, status=status.HTTP_204_NO_CONTENT)
        except Court.DoesNotExist:
            return Response({'error': 'Court non trouvé'}, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# BOOKING APIs
# ============================================================================

class BookingListView(APIView):
    """List and create bookings"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        status_filter = request.query_params.get('status', '')
        date_from = request.query_params.get('date_from', '')
        date_to = request.query_params.get('date_to', '')

        # Filter bookings based on user role
        bookings = Booking.objects.all()

        if request.user.is_authenticated:
            if is_admin_user(request.user):
                # Admin sees all bookings
                pass
            else:
                try:
                    profile = request.user.profile
                    if profile.role == 'manager':
                        # Manager sees bookings for their own clubs
                        bookings = bookings.filter(court__club__manager=request.user)
                    else:
                        # Players see only their own bookings
                        bookings = bookings.filter(user=request.user)
                except Exception:
                    # Fallback to only user's bookings if profile error
                    bookings = bookings.filter(user=request.user)
        else:
            return Response({'error': 'Authentification requise'}, status=status.HTTP_401_UNAUTHORIZED)

        # Update booking statuses
        for booking in bookings:
            booking.update_status()

        if status_filter:
            bookings = bookings.filter(status=status_filter)

        if date_from:
            bookings = bookings.filter(date__gte=date_from)

        if date_to:
            bookings = bookings.filter(date__lte=date_to)

        bookings = bookings.order_by('-date', '-start_time')

        serializer = BookingSerializer(bookings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new booking"""
        if hasattr(request.user, 'profile') and not request.user.profile.is_completed:
            return Response({
                'error': 'Vous devez compléter votre profil et définir votre niveau avant de réserver un terrain',
                'profile_incomplete': True
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = BookingSerializer(data=request.data)
        if serializer.is_valid():
            # Check for conflicts
            court_id = serializer.validated_data['court'].id
            date = serializer.validated_data['date']
            start_time = serializer.validated_data['start_time']

            existing = Booking.objects.filter(
                court_id=court_id,
                date=date,
                start_time=start_time,
                status__in=['confirmed']
            ).exists()

            if existing:
                return Response({'error': 'Ce créneau horaire est déjà réservé'}, status=status.HTTP_400_BAD_REQUEST)

            booking = serializer.save(user=request.user)

            # Send confirmation email
            from .email_service import send_booking_confirmation
            send_booking_confirmation(request.user, booking)

            # Send in-app notification to player
            try:
                date_str = booking.date.strftime('%d/%m/%Y')
                start_str = booking.start_time.strftime('%H:%M')
                club = booking.court.club
                create_notification(
                    user=request.user,
                    notification_type='booking_confirmed',
                    message=f"Votre réservation au club {club.name} le {date_str} à {start_str} a été confirmée !",
                    club=club,
                    target='mobile',
                    title="Réservation confirmée"
                )

                # Notify club manager on dashboard
                if club.manager and club.manager != request.user:
                    player_name = (request.user.profile.full_name or request.user.username) if hasattr(request.user, 'profile') else request.user.username
                    create_notification(
                        user=club.manager,
                        notification_type='new_booking',
                        message=f"Nouvelle réservation : {booking.court.name} le {date_str} à {start_str} par {player_name}",
                        club=club,
                        target='dashboard',
                        title="Nouvelle réservation reçue"
                    )
            except Exception as e:
                logger.error(f"Failed to send booking notifications: {e}")

            return Response(BookingSerializer(booking).data, status=status.HTTP_201_CREATED)

        from .exceptions import extract_first_error
        err_msg = extract_first_error(serializer.errors)
        return Response({'error': err_msg, 'detail': err_msg}, status=status.HTTP_400_BAD_REQUEST)


class BookingDetailView(APIView):
    """Booking detail API"""
    permission_classes = [IsAuthenticated]

    def get(self, request, booking_id):
        """Get booking details"""
        try:
            booking = Booking.objects.get(id=booking_id)
            # Check permission
            if booking.user != request.user and not is_admin_user(request.user):
                return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)

            booking.update_status()
            serializer = BookingSerializer(booking)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Booking.DoesNotExist:
            return Response({'error': 'Réservation non trouvée'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, booking_id):
        """Update booking status"""
        try:
            booking = Booking.objects.get(id=booking_id)
            # Check permission
            is_admin = is_admin_user(request.user)

            if booking.user != request.user and not is_admin:
                return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)

            new_status = request.data.get('status')
            allowed_statuses = ['cancelled', 'confirmed']
            if is_admin:
                allowed_statuses = ['confirmed', 'cancelled', 'completed']

            if new_status in allowed_statuses:
                old_status = booking.status
                booking.status = new_status
                booking.save()

                if new_status == 'confirmed' and old_status != 'confirmed':
                    # Send French confirmation email
                    try:
                        from .email_service import send_booking_confirmation_fr
                        send_booking_confirmation_fr(booking.user, booking)
                    except Exception as e:
                        print(f"Failed to send booking confirmation email: {e}")

                    # Send in-app notification
                    try:
                        date_str = booking.date.strftime('%d/%m/%Y')
                        start_str = booking.start_time.strftime('%H:%M')
                        msg = f"Votre réservation au club {booking.court.club.name} le {date_str} à {start_str} a été confirmée !"
                        create_notification(
                            user=booking.user,
                            notification_type='booking_confirmed',
                            message=msg,
                            club=booking.court.club,
                            target='mobile',
                            title="Réservation confirmée"
                        )
                    except Exception as e:
                        logger.error(f"Failed to create app notification: {e}")

                return Response(BookingSerializer(booking).data, status=status.HTTP_200_OK)
            return Response({'error': 'Statut invalide'}, status=status.HTTP_400_BAD_REQUEST)
        except Booking.DoesNotExist:
            return Response({'error': 'Réservation non trouvée'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, booking_id):
        """Cancel booking"""
        try:
            booking = Booking.objects.get(id=booking_id)
            # Check permission
            if booking.user != request.user and not is_admin_user(request.user):
                return Response({'error': 'Permission refusée'}, status=status.HTTP_403_FORBIDDEN)

            booking.status = 'cancelled'
            booking.save()

            # Notify user & manager
            try:
                date_str = booking.date.strftime('%d/%m/%Y')
                start_str = booking.start_time.strftime('%H:%M')
                club = booking.court.club
                # If cancelled by manager/admin, notify player
                if request.user != booking.user:
                    create_notification(
                        user=booking.user,
                        notification_type='booking_cancelled',
                        message=f"Votre réservation au club {club.name} le {date_str} à {start_str} a été annulée.",
                        club=club,
                        target='mobile',
                        title="Réservation annulée"
                    )
                # If cancelled by player, notify club manager on dashboard
                elif club.manager:
                    player_name = (booking.user.profile.full_name or booking.user.username) if hasattr(booking.user, 'profile') else booking.user.username
                    create_notification(
                        user=club.manager,
                        notification_type='booking_cancelled',
                        message=f"Réservation annulée : {booking.court.name} le {date_str} à {start_str} par {player_name}",
                        club=club,
                        target='dashboard',
                        title="Réservation annulée"
                    )
            except Exception as e:
                logger.error(f"Failed to send booking cancellation notifications: {e}")

            return Response({'message': 'Réservation annulée avec succès'}, status=status.HTTP_200_OK)

        except Booking.DoesNotExist:
            return Response({'error': 'Réservation non trouvée'}, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# MATCH APIs
# ============================================================================

class MatchListView(APIView):
    """List and create matches"""
    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [AllowAny]  # Allow public access to view matches

    def get(self, request):
        """Get matches with filters"""
        # Get filters
        status_filter = request.query_params.get('status', '')
        match_type = request.query_params.get('type', '')
        date_from = request.query_params.get('date_from', '')
        date_to = request.query_params.get('date_to', '')
        club_id = request.query_params.get('club_id', '')
        skill_level = request.query_params.get('skill_level', '')
        my_matches = request.query_params.get('my_matches', '')
        search = request.query_params.get('search', '')  # Add search parameter
        share_code = request.query_params.get('share_code', '')
        is_dashboard = request.query_params.get('dashboard') == 'true'
        is_edited_filter = request.query_params.get('is_edited', '')

        # Get blocked user IDs (only if authenticated)
        if request.user.is_authenticated:
            blocked_user_ids = BlockedUser.get_blocked_user_ids(request.user)
        else:
            blocked_user_ids = []

        # Base queryset - exclude blocked users
        matches = Match.objects.exclude(organizer_id__in=blocked_user_ids)

        # Quick lookup by share code
        if share_code:
            matches = matches.filter(share_code__iexact=share_code)
            for match in matches:
                match.update_status()
            serializer = MatchSerializer(matches, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        # Role-based filtering for managers in dashboard
        if request.user.is_authenticated and not is_admin_user(request.user):
            try:
                profile = request.user.profile
                if profile.role == 'manager':
                    # In dashboard context, restrict matches to their managed clubs
                    if is_dashboard:
                        matches = matches.filter(club__manager=request.user)
            except Exception:
                pass

        # Apply filters
        if status_filter:
            if status_filter == 'finished':
                matches = matches.filter(Q(status='completed') | Q(status='finished'))
            else:
                matches = matches.filter(status=status_filter)
        else:
            # By default, don't show cancelled matches in public feeds.
            # Allow them on the dashboard or for the user's own matches/history.
            if not is_dashboard and my_matches != 'true':
                matches = matches.exclude(status='cancelled')

        if match_type:
            matches = matches.filter(match_type=match_type)

        if is_edited_filter.lower() == 'true':
            matches = matches.filter(is_edited=True)
        elif is_edited_filter.lower() == 'false':
            matches = matches.filter(is_edited=False)

        if date_from:
            # Handle both date and datetime formats
            if 'T' in date_from:
                # ISO datetime format, extract just the date
                date_from = date_from.split('T')[0]
            matches = matches.filter(date_time__date__gte=date_from)

        if date_to:
            # Handle both date and datetime formats
            if 'T' in date_to:
                # ISO datetime format, extract just the date
                date_to = date_to.split('T')[0]
            matches = matches.filter(date_time__date__lte=date_to)

        if club_id:
            matches = matches.filter(club_id=club_id)

        if skill_level and skill_level.isdigit():
            level = int(skill_level)
            # Use the appropriate scale based on user's evaluation type
            user_eval_type = 'new'
            if request.user.is_authenticated and hasattr(request.user, 'profile'):
                user_eval_type = request.user.profile.evaluation_type
            if user_eval_type == 'old':
                matches = matches.filter(min_skill_level_old__lte=level, max_skill_level_old__gte=level)
            else:
                matches = matches.filter(min_skill_level_new__lte=level, max_skill_level_new__gte=level)

        # Add search functionality (search by club name or location)
        if search:
            matches = matches.filter(
                Q(title__icontains=search) |
                Q(club__name__icontains=search) |
                Q(club__city__icontains=search) |
                Q(club__address__icontains=search)
            )

        if my_matches == 'true' and request.user.is_authenticated:
            # Get matches where user is organizer or participant
            participant_matches = MatchParticipant.objects.filter(
                user=request.user,
                status='confirmed'
            ).values_list('match_id', flat=True)

            matches = matches.filter(
                Q(organizer=request.user) | Q(id__in=participant_matches)
            )
        else:
            # For available matches (not my matches), only show public matches
            if not is_dashboard:
                matches = matches.filter(is_public=True)
            # For non-authenticated users, only show open matches
            if not request.user.is_authenticated and not is_dashboard:
                matches = matches.filter(status='open')

        # Update match statuses
        for match in matches:
            match.update_status()

        # Order by date
        if is_dashboard:
            matches = matches.order_by('-date_time')
        else:
            matches = matches.order_by('date_time')

        # Paginate
        if is_dashboard:
            serializer = MatchSerializer(matches, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        paginator = PageNumberPagination()
        paginator.page_size = 20
        result_page = paginator.paginate_queryset(matches, request)

        serializer = MatchSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """Create a new match - Requires authentication"""
        if not request.user.is_authenticated:
            return Response({'error': 'Authentification requise pour créer des matchs'}, status=status.HTTP_401_UNAUTHORIZED)

        if hasattr(request.user, 'profile') and not request.user.profile.is_completed:
            return Response({
                'error': 'Vous devez compléter votre profil et définir votre niveau avant de créer un match',
                'profile_incomplete': True
            }, status=status.HTTP_400_BAD_REQUEST)

        serializer = MatchSerializer(data=request.data)
        if serializer.is_valid():
            match = serializer.save(organizer=request.user)

            # Auto-compute dual grille skill levels
            eval_type = match.evaluation_type or 'new'
            if eval_type == 'new':
                match.min_skill_level_new = match.min_skill_level
                match.max_skill_level_new = match.max_skill_level
                match.min_skill_level_old = max(1, round(match.min_skill_level * 10 / 8))
                match.max_skill_level_old = max(1, round(match.max_skill_level * 10 / 8))
            else:
                match.min_skill_level_old = match.min_skill_level
                match.max_skill_level_old = match.max_skill_level
                match.min_skill_level_new = max(1, round(match.min_skill_level * 8 / 10))
                match.max_skill_level_new = max(1, round(match.max_skill_level * 8 / 10))
            match.save()

            # Pass context when serializing the response
            response_serializer = MatchSerializer(match, context={'request': request})

            # Send confirmation email to match organizer
            try:
                send_match_creation_confirmation(request.user, match)
            except Exception as e:
                logger.error(f"Failed to send match creation email: {e}")

            # If match is created publicly, notify all friends of the creator
            if match.is_public:
                try:
                    creator_name = get_user_display_name(request.user)
                    friendships = Friendship.objects.filter(
                        Q(user1=request.user) | Q(user2=request.user)
                    ).select_related('user1', 'user2')
                    friends = [f.user2 if f.user1 == request.user else f.user1 for f in friendships]
                    for friend in friends:
                        create_notification(
                            user=friend,
                            notification_type='public_match_created',
                            match=match,
                            message=f'{creator_name} vient de créer un match public : "{match.title}". Rejoignez la partie !',
                            target='mobile',
                            title=f"Nouveau match de {creator_name}",
                            data={'match_id': str(match.id), 'type': 'public_match_created'}
                        )
                except Exception as e:
                    logger.error(f"Failed to notify friends about public match creation: {e}")

            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class MatchDetailView(APIView):
    """Match detail API"""
    permission_classes = [AllowAny]  # Allow public access to view match details

    def get(self, request, match_id):
        """Get match details"""
        try:
            match = Match.objects.get(id=match_id)
            match.update_status()

            serializer = MatchDetailSerializer(match, context={'request': request})
            data = serializer.data

            # Add user-specific info only if authenticated
            if request.user.is_authenticated:
                data['is_organizer'] = match.organizer == request.user
                data['is_participant'] = MatchParticipant.objects.filter(
                    match=match,
                    user=request.user,
                    status='confirmed'
                ).exists()
            else:
                data['is_organizer'] = False
                data['is_participant'] = False
                data['requires_login'] = True

            return Response(data, status=status.HTTP_200_OK)
        except Match.DoesNotExist:
            return Response({'error': 'Match non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, match_id):
        """Update match (organizer only)"""
        try:
            match = Match.objects.get(id=match_id)

            # Check permission
            is_admin = is_admin_user(request.user)
            if match.organizer != request.user and not is_admin:
                return Response({'error': 'Seul l\'organisateur ou un administrateur peut modifier le match'}, status=status.HTTP_403_FORBIDDEN)

            # Handle special actions
            action = request.data.get('action')
            if action == 'cancel':
                match.status = 'cancelled'
                match.is_open = False
                match.save()

                # Notify participants (including organizer and all confirmed players)
                users_to_notify = set()
                if match.organizer:
                    users_to_notify.add(match.organizer)
                for participant in match.participants.filter(status='confirmed'):
                    if participant.user:
                        users_to_notify.add(participant.user)

                for user in users_to_notify:
                    create_notification(
                        user=user,
                        notification_type='match_cancelled',
                        match=match,
                        message=f'Le match "{match.title}" a été annulé',
                        target='mobile',
                        title="Match annulé"
                    )

                    # Send cancellation email to confirmed players (excluding the organizer who cancelled)
                    if user != request.user:
                        try:
                            send_match_cancelled_email(user, match)
                        except Exception as e:
                            logger.error(f"Failed to send match cancelled email: {e}")

                return Response({'message': 'Match annulé avec succès'}, status=status.HTTP_200_OK)

            # Regular update
            is_only_status = set(request.data.keys()) <= {'status'}
            serializer = MatchSerializer(match, data=request.data, partial=True)
            if serializer.is_valid():
                if not is_only_status:
                    updated_match = serializer.save(is_edited=True, edited_at=timezone.now())
                    # Notify all match members (excluding the editor)
                    try:
                        members_to_notify = get_match_members(updated_match, exclude_user=request.user)
                        for member in members_to_notify:
                            create_notification(
                                user=member,
                                notification_type='match_edited',
                                match=updated_match,
                                message=f'Le match "{updated_match.title}" a été modifié par l\'organisateur. Consultez les nouvelles informations.',
                                target='mobile',
                                title="Match modifié",
                                data={'match_id': str(updated_match.id), 'type': 'match_edited'}
                            )
                    except Exception as e:
                        logger.error(f"Failed to send match edited notification: {e}")
                else:
                    serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Match.DoesNotExist:
            return Response({'error': 'Match non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, match_id):
        """Delete match (organizer only)"""
        try:
            match = Match.objects.get(id=match_id)

            # Check permission
            is_admin = is_admin_user(request.user)
            if match.organizer != request.user and not is_admin:
                return Response({'error': 'Seul l\'organisateur ou un administrateur peut supprimer le match'}, status=status.HTTP_403_FORBIDDEN)

            # Notify all match members via in-app notification & push before deletion
            try:
                date_str = (timezone.localtime(match.date_time) if timezone.is_aware(match.date_time) else match.date_time).strftime('%d/%m à %H:%M')
                members_to_notify = get_match_members(match, exclude_user=request.user)
                for member in members_to_notify:
                    create_notification(
                        user=member,
                        notification_type='match_deleted',
                        match=None,  # Decoupled from foreign key so deletion does not delete notification
                        message=f'Le match "{match.title}" prévu le {date_str} a été annulé et supprimé par l\'organisateur.',
                        target='mobile',
                        title="Match supprimé",
                        data={'match_title': match.title, 'type': 'match_deleted'}
                    )
            except Exception as e:
                logger.error(f"Failed to send match deleted notifications: {e}")

            # Notify confirmed participants via email before deletion
            for participant in match.participants.filter(status='confirmed'):
                if participant.user and participant.user != request.user:
                    try:
                        send_match_cancelled_email(participant.user, match)
                    except Exception as e:
                        logger.error(f"Failed to send match cancelled email: {e}")

            match.delete()
            return Response({'message': 'Match supprimé avec succès'}, status=status.HTTP_204_NO_CONTENT)
        except Match.DoesNotExist:
            return Response({'error': 'Match non trouvé'}, status=status.HTTP_404_NOT_FOUND)


class MatchJoinView(APIView):
    """Join/leave match"""
    permission_classes = [IsAuthenticated]

    def post(self, request, match_id):
        """Join a match"""
        try:
            if hasattr(request.user, 'profile') and not request.user.profile.is_completed:
                return Response({
                    'error': 'Vous devez compléter votre profil et définir votre niveau avant de rejoindre un match',
                    'profile_incomplete': True
                }, status=status.HTTP_400_BAD_REQUEST)

            match = Match.objects.get(id=match_id)

            # Check if match is open
            if match.status != 'open':
                return Response({'error': 'Le match n\'est pas ouvert aux inscriptions'}, status=status.HTTP_400_BAD_REQUEST)

            # Check skill level using user's evaluation type
            user_skill = request.user.profile.skill_level if hasattr(request.user, 'profile') else 5
            user_eval_type = request.user.profile.evaluation_type if hasattr(request.user, 'profile') else 'new'
            if user_eval_type == 'old':
                min_level = match.min_skill_level_old
                max_level = match.max_skill_level_old
            else:
                min_level = match.min_skill_level_new
                max_level = match.max_skill_level_new
            if user_skill < min_level or user_skill > max_level:
                return Response({'error': 'Votre niveau de jeu ne correspond pas aux exigences du match'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if already joined
            existing = MatchParticipant.objects.filter(match=match, user=request.user).first()
            if existing:
                if existing.status == 'confirmed':
                    return Response({'error': 'Vous avez déjà rejoint ce match'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # Update status
                    existing.status = 'confirmed'
                    existing.save()
                    return Response(MatchParticipantSerializer(existing).data, status=status.HTTP_200_OK)

            # Create participant
            participant = MatchParticipant.objects.create(
                match=match,
                user=request.user,
                status='confirmed'
            )

            # Update match status if full
            is_full = match.get_accepted_participants_count() >= match.max_players
            if is_full:
                match.status = 'full'
                match.is_open = False
                match.save()

            # Notify all match members (organizer + other confirmed players) in-app & push
            try:
                joined_name = get_user_display_name(request.user)
                members_to_notify = get_match_members(match, exclude_user=request.user)

                for member in members_to_notify:
                    is_org = (member == match.organizer)
                    if is_org:
                        msg = f'{joined_name} a rejoint votre match "{match.title}".' + (' Le match est maintenant complet !' if is_full else '')
                    else:
                        msg = f'{joined_name} a rejoint le match "{match.title}".' + (' Le match est maintenant complet !' if is_full else '')

                    create_notification(
                        user=member,
                        notification_type='match_player_joined',
                        match=match,
                        message=msg,
                        target='mobile',
                        title="Nouveau joueur dans le match",
                        data={'match_id': str(match.id), 'type': 'match_player_joined'}
                    )
            except Exception as e:
                logger.error(f"Failed to send player joined notifications: {e}")

            # Send confirmation email to the joining player
            try:
                send_match_join_confirmation(request.user, match)
            except Exception as e:
                logger.error(f"Failed to send match join confirmation email: {e}")

            # Send notification email to the match organizer
            if match.organizer and match.organizer != request.user:
                try:
                    send_player_joined_organizer_email(match.organizer, request.user, match)
                except Exception as e:
                    logger.error(f"Failed to send player joined organizer email: {e}")

            return Response(MatchParticipantSerializer(participant).data, status=status.HTTP_201_CREATED)
        except Match.DoesNotExist:
            return Response({'error': 'Match non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, match_id):
        """Leave a match"""
        try:
            match = Match.objects.get(id=match_id)
            participant = MatchParticipant.objects.filter(match=match, user=request.user).first()

            if not participant:
                return Response({'error': 'Vous ne participez pas à ce match'}, status=status.HTTP_400_BAD_REQUEST)

            quitter_name = get_user_display_name(request.user)
            members_to_notify = get_match_members(match, exclude_user=request.user)

            participant.delete()

            # Update match status if was full
            if match.status == 'full':
                match.status = 'open'
                match.is_open = True
                match.save()

            # Notify all remaining match members in-app & push
            try:
                for member in members_to_notify:
                    create_notification(
                        user=member,
                        notification_type='match_player_left',
                        match=match,
                        message=f'{quitter_name} a quitté le match "{match.title}". Une place est à nouveau disponible !',
                        target='mobile',
                        title="Désistement d'un joueur",
                        data={'match_id': str(match.id), 'type': 'match_player_left'}
                    )
            except Exception as e:
                logger.error(f"Failed to send player left notifications: {e}")

            return Response({'message': 'Vous avez quitté le match avec succès'}, status=status.HTTP_200_OK)
        except Match.DoesNotExist:
            return Response({'error': 'Match non trouvé'}, status=status.HTTP_404_NOT_FOUND)


class MatchParticipantManageView(APIView):
    """Manage match participants (organizer only)"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, match_id, participant_id):
        """Remove participant from match (organizer only)"""
        try:
            match = Match.objects.get(id=match_id)

            # Check if user is organizer
            if match.organizer != request.user:
                return Response({'error': 'Seul l\'organisateur peut retirer des participants'}, status=status.HTTP_403_FORBIDDEN)

            # Cannot remove player after match has ended or started
            match_start = match.get_match_datetime_start()
            if match.status in ['completed', 'cancelled'] or (match_start and match_start < timezone.now()):
                return Response({'error': 'Impossible de retirer un joueur d\'un match déjà commencé ou terminé'}, status=status.HTTP_400_BAD_REQUEST)

            # Find and remove participant
            participant = MatchParticipant.objects.filter(
                match=match,
                user_id=participant_id
            ).first()

            if not participant:
                return Response({'error': 'Participant non trouvé'}, status=status.HTTP_404_NOT_FOUND)

            removed_user = participant.user
            kicked_name = get_user_display_name(removed_user)

            # 1. Notify the removed participant in-app & push
            if removed_user:
                try:
                    create_notification(
                        user=removed_user,
                        notification_type='match_player_kicked',
                        match=match,
                        message=f'Vous avez été retiré du match "{match.title}" par l\'organisateur',
                        target='mobile',
                        title="Retiré du match",
                        data={'match_id': str(match.id), 'type': 'match_player_kicked'}
                    )
                except Exception as e:
                    logger.error(f"Failed to notify kicked player: {e}")

            # 2. Notify all other match members (excluding the organizer and the kicked player)
            try:
                other_members = get_match_members(match, exclude_user=request.user)
                if removed_user:
                    other_members.discard(removed_user)
                for member in other_members:
                    create_notification(
                        user=member,
                        notification_type='match_player_kicked',
                        match=match,
                        message=f'{kicked_name} a été retiré du match "{match.title}". Une place est libre !',
                        target='mobile',
                        title="Joueur retiré du match",
                        data={'match_id': str(match.id), 'type': 'match_player_kicked'}
                    )
            except Exception as e:
                logger.error(f"Failed to notify other match members about kicked player: {e}")

            # Send email to the removed player
            if removed_user:
                try:
                    send_player_kicked_email(removed_user, match, organizer=request.user)
                except Exception as e:
                    logger.error(f"Failed to send player removed email: {e}")

            participant.delete()

            # Update match status if was full
            if match.status == 'full':
                match.status = 'open'
                match.is_open = True
                match.save()

            return Response({'message': 'Participant retiré avec succès'}, status=status.HTTP_200_OK)
        except Match.DoesNotExist:
            return Response({'error': 'Match non trouvé'}, status=status.HTTP_404_NOT_FOUND)


class MatchInviteView(APIView):
    """Invite friends to a match"""
    permission_classes = [IsAuthenticated]

    def post(self, request, match_id):
        """Invite multiple friends to a match"""
        try:
            match = Match.objects.get(id=match_id)

            # Organizer or any confirmed match member can invite friends
            is_member = (match.organizer == request.user) or match.participants.filter(match=match, user=request.user, status='confirmed').exists()
            if not is_member:
                return Response({'error': 'Seuls les membres du match peuvent inviter des amis'}, status=status.HTTP_403_FORBIDDEN)

            # Get friend IDs from request
            friend_ids = request.data.get('friend_ids', [])

            if not friend_ids:
                return Response({'error': 'Aucun ami spécifié'}, status=status.HTTP_400_BAD_REQUEST)

            # Convert string IDs to integers if needed
            try:
                friend_ids = [int(fid) if isinstance(fid, str) else fid for fid in friend_ids]
            except (ValueError, TypeError):
                return Response({'error': 'Format d\'ID d\'utilisateur invalide'}, status=status.HTTP_400_BAD_REQUEST)

            results = []
            invited_count = 0
            inviter_name = get_user_display_name(request.user)

            for friend_id in friend_ids:
                try:
                    friend = User.objects.get(id=friend_id)

                    # Check if already a participant
                    is_participant = MatchParticipant.objects.filter(
                        match=match,
                        user=friend,
                        status='confirmed'
                    ).exists()

                    if is_participant or friend == match.organizer:
                        results.append({
                            'user_id': friend_id,
                            'username': friend.username,
                            'success': False,
                            'error': 'Déjà dans le match'
                        })
                        continue

                    # Check if already invited (has unread notification)
                    existing_invite = Notification.objects.filter(
                        user=friend,
                        match=match,
                        type='match_invite',
                        is_read=False
                    ).exists()

                    if existing_invite:
                        results.append({
                            'user_id': friend_id,
                            'username': friend.username,
                            'success': False,
                            'error': 'Déjà invité'
                        })
                        continue

                    # Create notification & send push
                    create_notification(
                        user=friend,
                        notification_type='match_invite',
                        match=match,
                        message=f'{inviter_name} vous a invité à rejoindre "{match.title}"',
                        target='mobile',
                        title="Invitation à un match",
                        data={'match_id': str(match.id), 'type': 'match_invite'}
                    )


                    results.append({
                        'user_id': friend_id,
                        'username': friend.username,
                        'success': True
                    })
                    invited_count += 1

                except User.DoesNotExist:
                    results.append({
                        'user_id': friend_id,
                        'success': False,
                        'error': 'Utilisateur non trouvé'
                    })

            return Response({
                'message': f'{invited_count} ami(s) invité(s) avec succès',
                'invited_count': invited_count,
                'total_requested': len(friend_ids),
                'results': results
            }, status=status.HTTP_200_OK)

        except Match.DoesNotExist:
            return Response({'error': 'Match non trouvé'}, status=status.HTTP_404_NOT_FOUND)


class MatchChatView(APIView):
    """Match chat messages"""
    permission_classes = [IsAuthenticated]

    def get(self, request, match_id):
        """Get match chat messages"""
        try:
            match = Match.objects.get(id=match_id)

            # Check if user is participant or organizer
            is_participant = MatchParticipant.objects.filter(
                match=match,
                user=request.user,
                status='confirmed'
            ).exists()

            if not (match.organizer == request.user or is_participant):
                return Response({'error': 'Non autorisé à voir le chat'}, status=status.HTTP_403_FORBIDDEN)

            messages = match.messages.all().order_by('created_at')
            serializer = MatchMessageSerializer(messages, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Match.DoesNotExist:
            return Response({'error': 'Match non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, match_id):
        """Send message in match chat"""
        try:
            match = Match.objects.get(id=match_id)

            # Check if user is participant or organizer
            is_participant = MatchParticipant.objects.filter(
                match=match,
                user=request.user,
                status='confirmed'
            ).exists()

            if not (match.organizer == request.user or is_participant):
                return Response({'error': 'Non autorisé à envoyer des messages'}, status=status.HTTP_403_FORBIDDEN)

            content = request.data.get('content')
            if not content:
                return Response({'error': 'Le contenu du message est requis'}, status=status.HTTP_400_BAD_REQUEST)

            message = MatchMessage.objects.create(
                match=match,
                sender=request.user,
                content=content
            )

            serializer = MatchMessageSerializer(message)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Match.DoesNotExist:
            return Response({'error': 'Match non trouvé'}, status=status.HTTP_404_NOT_FOUND)


class MatchCommentView(APIView):
    """Match comments & Q&A (available exclusively on public matches)"""
    permission_classes = [IsAuthenticated]

    def get(self, request, match_id):
        """Get top-level comments and nested replies for a public match"""
        try:
            match = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            return Response({'error': 'Match non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        # Comments only allowed on public matches (admins can view all)
        if not match.is_public and not is_admin_user(request.user):
            return Response(
                {'error': 'Les commentaires ne sont pas activés pour les matchs privés.'},
                status=status.HTTP_403_FORBIDDEN
            )

        comments = match.comments.filter(parent_comment__isnull=True).select_related(
            'author__profile'
        ).prefetch_related(
            'replies__author__profile'
        ).order_by('created_at')

        serializer = MatchCommentSerializer(comments, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, match_id):
        """Post a comment or reply to an existing comment on a public match"""
        try:
            match = Match.objects.get(id=match_id)
        except Match.DoesNotExist:
            return Response({'error': 'Match non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        # STRICT RULE: Comments only allowed on public matches
        if not match.is_public:
            return Response(
                {'error': 'Impossible de commenter sur un match privé.'},
                status=status.HTTP_403_FORBIDDEN
            )

        content = request.data.get('content', '').strip()
        if not content:
            return Response({'error': 'Le commentaire ne peut pas être vide.'}, status=status.HTTP_400_BAD_REQUEST)

        if len(content) > 1000:
            return Response({'error': 'Le commentaire ne doit pas dépasser 1000 caractères.'}, status=status.HTTP_400_BAD_REQUEST)

        parent_comment_id = request.data.get('parent_comment_id')
        parent_comment = None
        if parent_comment_id:
            try:
                parent_comment = MatchComment.objects.get(id=parent_comment_id, match=match)
            except MatchComment.DoesNotExist:
                return Response({'error': 'Commentaire parent non trouvé.'}, status=status.HTTP_400_BAD_REQUEST)

        comment = MatchComment.objects.create(
            match=match,
            author=request.user,
            content=content,
            parent_comment=parent_comment
        )

        # Dispatch notifications to organizer and confirmed participants
        confirmed_participants = match.participants.filter(status='confirmed').select_related('user')
        recipients_set = {match.organizer} | {p.user for p in confirmed_participants if p.user}

        # If replying, also notify the original question author
        if parent_comment and parent_comment.author:
            recipients_set.add(parent_comment.author)

        # Exclude commenter
        recipients = [u for u in recipients_set if u and u != request.user]

        author_display_name = get_user_display_name(request.user)

        for recipient in recipients:
            is_reply = parent_comment is not None
            title = f"Réponse sur {match.title}" if is_reply else f"Nouveau commentaire sur {match.title}"
            body_preview = content[:60] + ('...' if len(content) > 60 else '')
            message_text = f"{author_display_name} : {body_preview}"

            try:
                create_notification(
                    user=recipient,
                    notification_type='match_comment',
                    title=title,
                    message=message_text,
                    match=match,
                    target='mobile',
                    data={
                        'match_id': str(match.id),
                        'comment_id': str(comment.id),
                        'type': 'match_comment',
                    }
                )
            except Exception as e:
                logger.error(f"Error sending match comment notification to {recipient.username}: {e}")

        serializer = MatchCommentSerializer(comment, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MatchCommentDetailView(APIView):
    """Delete match comment"""
    permission_classes = [IsAuthenticated]

    def delete(self, request, match_id, comment_id):
        try:
            comment = MatchComment.objects.get(id=comment_id, match_id=match_id)
        except MatchComment.DoesNotExist:
            return Response({'error': 'Commentaire non trouvé.'}, status=status.HTTP_404_NOT_FOUND)

        is_author = comment.author == request.user
        is_organizer = comment.match.organizer == request.user
        if not (is_author or is_organizer or is_admin_user(request.user)):
            return Response({'error': 'Non autorisé à supprimer ce commentaire.'}, status=status.HTTP_403_FORBIDDEN)

        comment.delete()
        return Response({'message': 'Commentaire supprimé avec succès.'}, status=status.HTTP_200_OK)


class AdminCommentModerationView(APIView):
    """Admin endpoint to view, search, and moderate all match comments across public matches"""
    permission_classes = [IsAdminUserRole]

    def get(self, request):
        search = request.query_params.get('search', '').strip()
        match_id = request.query_params.get('match_id')
        comment_type = request.query_params.get('type')  # 'parent', 'reply', or 'all'

        comments = MatchComment.objects.select_related(
            'match', 'match__club', 'match__court', 'author', 'author__profile',
            'parent_comment', 'parent_comment__author', 'parent_comment__author__profile'
        ).prefetch_related('replies').order_by('-created_at')

        if match_id:
            comments = comments.filter(match_id=match_id)

        if comment_type == 'parent':
            comments = comments.filter(parent_comment__isnull=True)
        elif comment_type == 'reply':
            comments = comments.filter(parent_comment__isnull=False)

        if search:
            comments = comments.filter(
                Q(content__icontains=search) |
                Q(author__username__icontains=search) |
                Q(author__profile__full_name__icontains=search) |
                Q(match__title__icontains=search) |
                Q(match__club__name__icontains=search)
            )

        paginator = PageNumberPagination()
        try:
            page_size = int(request.query_params.get('page_size', 20))
            paginator.page_size = min(max(page_size, 1), 100)
        except (ValueError, TypeError):
            paginator.page_size = 20

        paginated_comments = paginator.paginate_queryset(comments, request)
        serializer = AdminCommentSerializer(paginated_comments, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)


class AdminCommentDetailView(APIView):
    """Admin endpoint to delete any comment directly by comment ID"""
    permission_classes = [IsAdminUserRole]

    def delete(self, request, comment_id):
        try:
            comment = MatchComment.objects.get(id=comment_id)
        except MatchComment.DoesNotExist:
            return Response({'error': 'Commentaire non trouvé.'}, status=status.HTTP_404_NOT_FOUND)

        comment.delete()
        return Response({'message': 'Commentaire supprimé avec succès.'}, status=status.HTTP_200_OK)


class AdminBulkDeleteView(APIView):
    """Admin endpoint to bulk delete entities (users, players, clubs, courts, matches, comments, bookings)"""
    permission_classes = [IsAdminUserRole]

    def post(self, request):
        entity = request.data.get('entity')
        ids = request.data.get('ids', [])

        if not entity or not isinstance(ids, list) or len(ids) == 0:
            return Response({'error': 'Entité et liste d\'identifiants requises.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            ids = [int(i) for i in ids]
        except (ValueError, TypeError):
            return Response({'error': 'Identifiants invalides.'}, status=status.HTTP_400_BAD_REQUEST)

        deleted_count = 0

        if entity in ['users', 'players']:
            qs = User.objects.filter(id__in=ids).exclude(id=request.user.id)
            deleted_count = qs.count()
            qs.delete()

        elif entity == 'clubs':
            qs = Club.objects.filter(id__in=ids)
            deleted_count = qs.count()
            qs.delete()

        elif entity == 'courts':
            qs = Court.objects.filter(id__in=ids)
            deleted_count = qs.count()
            qs.delete()

        elif entity == 'matches':
            qs = Match.objects.filter(id__in=ids)
            deleted_count = qs.count()
            qs.delete()

        elif entity == 'comments':
            qs = MatchComment.objects.filter(id__in=ids)
            deleted_count = qs.count()
            qs.delete()

        elif entity == 'bookings':
            qs = Booking.objects.filter(id__in=ids)
            deleted_count = qs.count()
            qs.delete()

        else:
            return Response({'error': f'Entité "{entity}" non supportée.'}, status=status.HTTP_400_BAD_REQUEST)

        return Response({
            'message': f'{deleted_count} éléments supprimés avec succès.',
            'deleted_count': deleted_count
        }, status=status.HTTP_200_OK)


class MatchFinishView(APIView):
    """Mark match as finished/completed with winners and losers"""
    permission_classes = [IsAuthenticated]

    def post(self, request, match_id):
        """Finish a match and mark winners/losers"""
        try:
            match = Match.objects.get(id=match_id)

            # Only organizer can finish the match
            if match.organizer != request.user:
                return Response({'error': 'Seul l\'organisateur peut marquer le match comme terminé'}, status=status.HTTP_403_FORBIDDEN)

            # Check if match time has passed or is in progress
            if not (match.is_in_progress() or match.is_completed()):
                return Response({'error': 'Le match n\'est pas encore commencé'}, status=status.HTTP_400_BAD_REQUEST)

            # Get winner and loser IDs from request
            winner_ids = request.data.get('winner_ids', [])
            loser_ids = request.data.get('loser_ids', [])

            # Convert string IDs to integers (frontend sends strings)
            try:
                winner_ids = [int(wid) if isinstance(wid, str) else wid for wid in winner_ids]
                loser_ids = [int(lid) if isinstance(lid, str) else lid for lid in loser_ids]
            except (ValueError, TypeError):
                return Response({'error': 'Format d\'ID d\'utilisateur invalide'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if all users are participants
            for winner_id in winner_ids:
                if not match.participants.filter(user_id=winner_id, status='confirmed').exists() and match.organizer.id != winner_id:
                    return Response({'error': f'L\'utilisateur {winner_id} n\'est pas un participant'}, status=status.HTTP_400_BAD_REQUEST)

            for loser_id in loser_ids:
                if not match.participants.filter(user_id=loser_id, status='confirmed').exists() and match.organizer.id != loser_id:
                    return Response({'error': f'L\'utilisateur {loser_id} n\'est pas un participant'}, status=status.HTTP_400_BAD_REQUEST)

            was_already_completed = (match.status == 'completed' and match.winners.exists())

            # Mark match as completed
            match.status = 'completed'
            match.is_open = False
            match.save()

            # Mark winners and losers
            success = match.mark_winners(winner_ids, loser_ids)

            if success:
                # Collect other confirmed participants (excluding organizer / current user)
                # If only one player (organizer/creator) is in the match, do not send notification
                other_participants = match.participants.filter(status='confirmed').exclude(user=request.user)

                if other_participants.exists():
                    # Format winner display names
                    winners = User.objects.filter(id__in=winner_ids)
                    def get_user_display_name(u):
                        if hasattr(u, 'profile') and u.profile.full_name and u.profile.full_name.strip():
                            return u.profile.full_name.strip()
                        fn = f"{u.first_name} {u.last_name}".strip()
                        return fn if fn else u.username

                    winner_names = [get_user_display_name(w) for w in winners]
                    if len(winner_names) == 1:
                        winners_text = winner_names[0]
                    elif len(winner_names) == 2:
                        winners_text = f"{winner_names[0]} et {winner_names[1]}"
                    elif len(winner_names) > 2:
                        winners_text = ", ".join(winner_names[:-1]) + f" et {winner_names[-1]}"
                    else:
                        winners_text = ""

                    if was_already_completed:
                        title = "Résultats mis à jour"
                        if winners_text:
                            message = f'Les vainqueurs du match "{match.title}" sont : {winners_text}. N\'oubliez pas de noter les autres joueurs !'
                        else:
                            message = f'Les résultats du match "{match.title}" ont été mis à jour. N\'oubliez pas de noter les autres joueurs !'
                    else:
                        title = "Match terminé"
                        if winners_text:
                            message = f'Le match "{match.title}" est terminé ! Les vainqueurs sont : {winners_text}. N\'oubliez pas de noter les autres joueurs !'
                        else:
                            message = f'Le match "{match.title}" est terminé. N\'oubliez pas de noter les autres joueurs !'

                    for participant in other_participants:
                        create_notification(
                            user=participant.user,
                            notification_type='match_ended',
                            match=match,
                            message=message,
                            target='mobile',
                            title=title,
                            data={
                                'action': 'rate_match',
                                'match_id': str(match.id),
                            }
                        )

                return Response({
                    'message': 'Résultats du match mis à jour avec succès' if was_already_completed else 'Match marqué comme terminé avec succès',
                    'match_id': match.id,
                    'status': match.status
                }, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Échec de l\'enregistrement des vainqueurs/perdants'}, status=status.HTTP_400_BAD_REQUEST)

        except Match.DoesNotExist:
            return Response({'error': 'Match non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============================================================================
# RATING APIs
# ============================================================================

class PlayerRatingView(APIView):
    """Player rating API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get ratings"""
        match_id = request.query_params.get('match_id')
        user_id = request.query_params.get('user_id')

        if match_id:
            # Get ratings for a specific match
            ratings = Rating.objects.filter(match_id=match_id)
        elif user_id:
            # Get ratings for a specific user
            ratings = Rating.objects.filter(rated_user_id=user_id)
        else:
            # Get ratings received by current user
            ratings = Rating.objects.filter(rated_user=request.user)

        serializer = RatingSerializer(ratings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Rate a player"""
        # Debug logging
        print('=== Rating API Debug ===')
        print(f'Request data: {request.data}')
        print(f'Request user: {request.user.id} ({request.user.username})')

        serializer = RatingSerializer(data=request.data)
        if serializer.is_valid():
            match_id = serializer.validated_data['match'].id
            rated_user_id = serializer.validated_data['rated_user'].id
            print(f'Valid data - Match: {match_id}, Rated user: {rated_user_id}')

            # Check if match is completed
            match = Match.objects.get(id=match_id)
            if match.status != 'completed':
                return Response({'error': 'L\'évaluation n\'est possible qu\'après la fin du match'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if user was in the match
            was_participant = (
                match.organizer == request.user or
                MatchParticipant.objects.filter(
                    match=match,
                    user=request.user,
                    status='confirmed'
                ).exists()
            )

            if not was_participant:
                return Response({'error': 'Vous ne participiez pas à ce match'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if already rated
            existing = Rating.objects.filter(
                match_id=match_id,
                rater=request.user,
                rated_user_id=rated_user_id
            ).exists()

            if existing:
                return Response({'error': 'Vous avez déjà évalué ce joueur pour ce match'}, status=status.HTTP_400_BAD_REQUEST)

            rating = serializer.save(rater=request.user)

            # Update rated user's public rating
            rated_user = User.objects.get(id=rated_user_id)
            if hasattr(rated_user, 'profile'):
                rated_user.profile.update_public_rating()

            print('Rating saved successfully')
            print('=== End Debug ===')
            return Response(RatingSerializer(rating).data, status=status.HTTP_201_CREATED)

        print(f'Serializer errors: {serializer.errors}')
        print('=== End Debug ===')
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CourtRatingView(APIView):
    """Court rating API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get court ratings"""
        court_id = request.query_params.get('court_id')
        club_id = request.query_params.get('club_id')

        if court_id:
            ratings = CourtRating.objects.filter(court_id=court_id)
        elif club_id:
            ratings = CourtRating.objects.filter(court__club_id=club_id)
        else:
            ratings = CourtRating.objects.filter(rater=request.user)

        serializer = CourtRatingSerializer(ratings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Rate a court"""
        serializer = CourtRatingSerializer(data=request.data)
        if serializer.is_valid():
            court_id = serializer.validated_data['court'].id
            match_id = serializer.validated_data['match'].id

            # Check if already rated
            existing = CourtRating.objects.filter(
                court_id=court_id,
                match_id=match_id,
                rater=request.user
            ).exists()

            if existing:
                return Response({'error': 'Vous avez déjà évalué ce terrain pour ce match'}, status=status.HTTP_400_BAD_REQUEST)

            rating = serializer.save(rater=request.user)

            # Update club rating
            court = Court.objects.get(id=court_id)
            court.club.update_rating()

            return Response(CourtRatingSerializer(rating).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PendingRatingMatchView(APIView):
    """Check if the authenticated user has a completed match (<48h) pending peer ratings or winner declaration"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        now = timezone.now()
        cutoff = now - timedelta(hours=48)

        # Get matches where user was organizer or confirmed participant
        participant_match_ids = MatchParticipant.objects.filter(
            user=user,
            status='confirmed'
        ).values_list('match_id', flat=True)

        candidate_matches = Match.objects.filter(
            Q(organizer=user) | Q(id__in=participant_match_ids)
        ).filter(
            date_time__gte=cutoff - timedelta(hours=6)
        ).order_by('-date_time')

        for match in candidate_matches:
            match.update_status()

            match_end = match.get_match_datetime_end()
            # Match must be finished
            if match.status != 'completed' and match_end > now:
                continue

            # Must be within 48h from end
            if now > match_end + timedelta(hours=48):
                continue

            # Check if user has already rated peers for this match
            if Rating.objects.filter(match=match, rater=user).exists():
                continue

            # Check if there are other confirmed players in the match to rate
            all_confirmed = set(match.participants.filter(status='confirmed').values_list('user_id', flat=True))
            all_confirmed.add(match.organizer_id)
            all_confirmed.discard(user.id)
            has_players_to_rate = len(all_confirmed) > 0

            # If user has no one to rate and is not organizer, skip
            if not has_players_to_rate and match.organizer_id != user.id:
                continue

            # Found pending match
            serializer = MatchSerializer(match, context={'request': request})
            hours_remaining = round(max(0.0, (match_end + timedelta(hours=48) - now).total_seconds() / 3600.0), 1)

            return Response({
                'has_pending_rating': True,
                'match': serializer.data,
                'is_organizer': (match.organizer_id == user.id),
                'winner_defined': (match.winners.exists() or match.losers.exists()),
                'has_players_to_rate': has_players_to_rate,
                'hours_remaining': hours_remaining,
            }, status=status.HTTP_200_OK)

        return Response({
            'has_pending_rating': False,
            'match': None,
        }, status=status.HTTP_200_OK)


# ============================================================================
# COMMUNITY APIs
# ============================================================================

class CommunityPostView(APIView):
    """Community posts API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get community posts"""
        category = request.query_params.get('category', '')
        city = request.query_params.get('city', '')
        group_id = request.query_params.get('group_id', '')

        posts = CommunityPost.objects.all()

        if category:
            posts = posts.filter(category=category)
        if city:
            posts = posts.filter(city__icontains=city)
        if group_id:
            posts = posts.filter(group_id=group_id)

        posts = posts.order_by('-created_at')

        # Paginate
        paginator = PageNumberPagination()
        paginator.page_size = 20
        result_page = paginator.paginate_queryset(posts, request)

        serializer = CommunityPostSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)

    def post(self, request):
        """Create a community post"""
        serializer = CommunityPostSerializer(data=request.data)
        if serializer.is_valid():
            post = serializer.save(author=request.user)
            return Response(CommunityPostSerializer(post, context={'request': request}).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PostLikeView(APIView):
    """Like/unlike posts"""
    permission_classes = [IsAuthenticated]

    def post(self, request, post_id):
        """Toggle like on a post"""
        try:
            post = CommunityPost.objects.get(id=post_id)
            if post.likes.filter(id=request.user.id).exists():
                post.likes.remove(request.user)
                liked = False
            else:
                post.likes.add(request.user)
                liked = True

            return Response({
                'liked': liked,
                'like_count': post.like_count
            }, status=status.HTTP_200_OK)
        except CommunityPost.DoesNotExist:
            return Response({'error': 'Publication non trouvée'}, status=status.HTTP_404_NOT_FOUND)


class PostReplyView(APIView):
    """Post replies API"""
    permission_classes = [IsAuthenticated]

    def get(self, request, post_id):
        """Get replies for a post"""
        try:
            post = CommunityPost.objects.get(id=post_id)
            replies = post.replies.filter(parent_reply__isnull=True)
            serializer = PostReplySerializer(replies, many=True, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except CommunityPost.DoesNotExist:
            return Response({'error': 'Publication non trouvée'}, status=status.HTTP_404_NOT_FOUND)

    def post(self, request, post_id):
        """Create a reply"""
        try:
            post = CommunityPost.objects.get(id=post_id)
            content = request.data.get('content')
            parent_reply_id = request.data.get('parent_reply_id')

            if not content:
                return Response({'error': 'Contenu requis'}, status=status.HTTP_400_BAD_REQUEST)

            reply = PostReply.objects.create(
                post=post,
                author=request.user,
                content=content,
                parent_reply_id=parent_reply_id if parent_reply_id else None
            )

            serializer = PostReplySerializer(reply, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except CommunityPost.DoesNotExist:
            return Response({'error': 'Publication non trouvée'}, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# FRIEND SYSTEM APIs
# ============================================================================

class FriendRequestView(APIView):
    """Friend requests API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get friend requests"""
        # Get pending requests only
        received = FriendRequest.objects.filter(
            receiver=request.user,
            status='pending'
        )
        sent = FriendRequest.objects.filter(
            sender=request.user,
            status='pending'  # Only show pending sent requests
        )

        return Response({
            'received': FriendRequestSerializer(received, many=True).data,
            'sent': FriendRequestSerializer(sent, many=True).data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        """Send friend request"""
        receiver_id = request.data.get('receiver_id')
        message = request.data.get('message', '')

        try:
            receiver = User.objects.get(id=receiver_id)

            if receiver == request.user:
                return Response({'error': 'Vous ne pouvez pas vous envoyer de demande d\'ami'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if already friends
            if Friendship.are_friends(request.user, receiver):
                return Response({'error': 'Déjà amis'}, status=status.HTTP_400_BAD_REQUEST)

            # Check if request already exists
            existing = FriendRequest.objects.filter(
                Q(sender=request.user, receiver=receiver) |
                Q(sender=receiver, receiver=request.user)
            ).first()

            if existing:
                if existing.status == 'pending':
                    return Response({'error': 'Demande d\'ami déjà en cours'}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    # Delete old request (accepted/rejected) before creating new one
                    existing.delete()

            # Create friend request
            friend_request = FriendRequest.objects.create(
                sender=request.user,
                receiver=receiver,
                message=message
            )

            sender_name = get_user_display_name(request.user)

            # Send notification & push
            create_notification(
                user=receiver,
                notification_type='friend_request',
                friend_request=friend_request,
                message=f"{sender_name} vous a envoyé une demande d'ami",
                target='mobile',
                title="Demande d'ami",
                data={'friend_request_id': str(friend_request.id), 'type': 'friend_request'}
            )

            return Response(FriendRequestSerializer(friend_request).data, status=status.HTTP_201_CREATED)

        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)


class FriendRequestManageView(APIView):
    """Manage friend requests"""
    permission_classes = [IsAuthenticated]

    def put(self, request, request_id):
        """Accept/reject friend request"""
        action = request.data.get('action')  # 'accept' or 'reject'

        try:
            friend_request = FriendRequest.objects.get(
                id=request_id,
                receiver=request.user,
                status='pending'
            )

            if action == 'accept':
                # Create friendship
                Friendship.objects.create(
                    user1=min(friend_request.sender, friend_request.receiver, key=lambda u: u.id),
                    user2=max(friend_request.sender, friend_request.receiver, key=lambda u: u.id)
                )
                friend_request.status = 'accepted'
                friend_request.save()

                responder_name = get_user_display_name(request.user)

                # Notify sender in-app & push
                create_notification(
                    user=friend_request.sender,
                    notification_type='friend_accepted',
                    friend_request=friend_request,
                    message=f"{responder_name} a accepté votre demande d'ami",
                    target='mobile',
                    title="Demande d'ami acceptée",
                    data={'friend_request_id': str(friend_request.id), 'type': 'friend_accepted'}
                )


                return Response({'message': 'Demande d\'ami acceptée'}, status=status.HTTP_200_OK)

            elif action == 'reject':
                friend_request.status = 'rejected'
                friend_request.save()
                return Response({'message': 'Demande d\'ami refusée'}, status=status.HTTP_200_OK)

            else:
                return Response({'error': 'Action invalide'}, status=status.HTTP_400_BAD_REQUEST)

        except FriendRequest.DoesNotExist:
            return Response({'error': 'Demande d\'ami non trouvée'}, status=status.HTTP_404_NOT_FOUND)


class FriendsListView(APIView):
    """Friends list API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's friends with optional fuzzy search"""
        friendships = Friendship.objects.filter(
            Q(user1=request.user) | Q(user2=request.user)
        )

        search = request.query_params.get('q', '').strip()
        if search:
            s_lower = search.lower()
            matching_ids = []
            import difflib
            for f in friendships:
                friend = f.user2 if f.user1 == request.user else f.user1
                full_name = f"{friend.first_name} {friend.last_name}".strip().lower()
                username = friend.username.lower()
                email = (friend.email or '').lower()

                if (s_lower in username or s_lower in full_name or s_lower in email or
                    difflib.SequenceMatcher(None, s_lower, username).ratio() > 0.65 or
                    difflib.SequenceMatcher(None, s_lower, full_name).ratio() > 0.65):
                    matching_ids.append(f.id)

            friendships = friendships.filter(id__in=matching_ids)

        serializer = FriendshipSerializer(friendships, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, friend_id):
        """Remove friend"""
        try:
            friend = User.objects.get(id=friend_id)

            friendship = Friendship.objects.filter(
                Q(user1=request.user, user2=friend) |
                Q(user1=friend, user2=request.user)
            ).first()

            if friendship:
                friendship.delete()
                return Response({'message': 'Ami retiré'}, status=status.HTTP_200_OK)
            else:
                return Response({'error': 'Pas amis'}, status=status.HTTP_400_BAD_REQUEST)

        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)


class FriendSuggestionsView(APIView):
    """Suggestions of players to add as friends with pagination and typo-tolerant search"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            page = int(request.query_params.get('page', 1))
            page_size = int(request.query_params.get('page_size', 10))
        except (ValueError, TypeError):
            page = 1
            page_size = 10

        search = request.query_params.get('q', '').strip()

        # 1. Existing friends IDs
        friend_ids = set()
        for f in Friendship.objects.filter(Q(user1=request.user) | Q(user2=request.user)):
            friend_ids.add(f.user2_id if f.user1_id == request.user.id else f.user1_id)

        # 2. Friend requests (pending, accepted, rejected)
        all_reqs = FriendRequest.objects.filter(
            Q(sender=request.user) | Q(receiver=request.user)
        )
        req_user_ids = set()
        sent_pending_ids = set()
        for fr in all_reqs:
            other_id = fr.receiver_id if fr.sender_id == request.user.id else fr.sender_id
            if fr.status == 'pending':
                req_user_ids.add(other_id)
                if fr.sender_id == request.user.id:
                    sent_pending_ids.add(other_id)
            elif fr.status in ('rejected', 'accepted'):
                req_user_ids.add(other_id)

        # 3. Blocked users
        blocked_user_ids = set(BlockedUser.get_blocked_user_ids(request.user))

        # Excluded from suggestions
        excluded_ids = friend_ids | req_user_ids | blocked_user_ids | {request.user.id}

        users_qs = User.objects.filter(is_active=True).exclude(id__in=excluded_ids)

        if search:
            search_str = search.strip()
            exact_matches = users_qs.filter(
                Q(username__icontains=search_str) |
                Q(first_name__icontains=search_str) |
                Q(last_name__icontains=search_str) |
                Q(email__icontains=search_str)
            )
            if exact_matches.exists():
                users_qs = exact_matches
            else:
                import difflib
                candidates = list(users_qs[:100])
                s_lower = search_str.lower()
                matched_ids = []
                for u in candidates:
                    u_full = f"{u.first_name} {u.last_name}".strip().lower()
                    u_user = u.username.lower()
                    u_email = (u.email or '').lower()
                    if (s_lower in u_user or s_lower in u_full or s_lower in u_email or
                        difflib.SequenceMatcher(None, s_lower, u_user).ratio() > 0.65 or
                        difflib.SequenceMatcher(None, s_lower, u_full).ratio() > 0.65):
                        matched_ids.append(u.id)
                users_qs = users_qs.filter(id__in=matched_ids)

        # Order by location proximity to user profile if available, then date_joined
        user_location = getattr(getattr(request.user, 'profile', None), 'location', None)
        if user_location:
            users_qs = users_qs.order_by(
                Case(
                    When(profile__location__iexact=user_location, then=0),
                    default=1,
                    output_field=IntegerField(),
                ),
                '-date_joined'
            )
        else:
            users_qs = users_qs.order_by('-date_joined')

        total = users_qs.count()
        start = (page - 1) * page_size
        end = start + page_size
        page_users = users_qs[start:end]
        has_more = end < total

        results = []
        for u in page_users:
            full_name = f"{u.first_name} {u.last_name}".strip()
            avatar_url = None
            if hasattr(u, 'profile') and u.profile.avatar:
                try:
                    avatar_url = request.build_absolute_uri(u.profile.avatar.url)
                except Exception:
                    avatar_url = u.profile.avatar.url

            results.append({
                'id': u.id,
                'username': u.username,
                'full_name': full_name if full_name else u.username,
                'email': u.email,
                'avatar': avatar_url,
                'skill_level': u.profile.skill_level if hasattr(u, 'profile') else None,
                'evaluation_type': u.profile.evaluation_type if hasattr(u, 'profile') else 'new',
                'city': u.profile.location if hasattr(u, 'profile') else '',
                'has_pending_request': u.id in sent_pending_ids,
                'is_friend': False,
            })

        return Response({
            'suggestions': results,
            'page': page,
            'page_size': page_size,
            'total': total,
            'has_more': has_more,
        }, status=status.HTTP_200_OK)


# ============================================================================
# NOTIFICATION APIs
# ============================================================================

class NotificationView(APIView):
    """Notifications API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's notifications (supports unread_only and target filters)"""
        unread_only = request.query_params.get('unread_only', 'false').lower() == 'true'
        target = request.query_params.get('target')

        # Delete notifications older than 90 days for this user
        three_months_ago = timezone.now() - timedelta(days=90)
        Notification.objects.filter(user=request.user, created_at__lt=three_months_ago).delete()

        notifications = Notification.objects.filter(user=request.user)

        if target:
            notifications = notifications.filter(target__in=[target, 'both'])

        if unread_only:
            notifications = notifications.filter(is_read=False)

        notifications = notifications.order_by('-created_at')[:50]

        serializer = NotificationSerializer(notifications, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        """Mark notifications as read"""
        notification_ids = request.data.get('notification_ids', [])

        if notification_ids:
            Notification.objects.filter(
                id__in=notification_ids,
                user=request.user
            ).update(is_read=True)
        else:
            # Mark all as read (optional target filter)
            target = request.data.get('target')
            qs = Notification.objects.filter(user=request.user, is_read=False)
            if target:
                qs = qs.filter(target__in=[target, 'both'])
            qs.update(is_read=True)

        return Response({'message': 'Notifications marquées comme lues'}, status=status.HTTP_200_OK)

    def delete(self, request, pk=None):
        """Delete notifications: single by url/param/body, bulk by IDs, or bulk all (with optional target filter)"""
        notification_id = pk or request.query_params.get('id') or request.data.get('id')
        notification_ids = request.data.get('notification_ids', [])
        target = request.query_params.get('target') or request.data.get('target')

        if notification_id:
            deleted_count, _ = Notification.objects.filter(
                id=notification_id,
                user=request.user
            ).delete()
            if deleted_count == 0:
                return Response({'error': 'Notification non trouvée'}, status=status.HTTP_404_NOT_FOUND)
            return Response(
                {'message': 'Notification supprimée', 'deleted_count': deleted_count},
                status=status.HTTP_200_OK
            )

        if notification_ids:
            deleted_count, _ = Notification.objects.filter(
                id__in=notification_ids,
                user=request.user
            ).delete()
            return Response(
                {'message': f'{deleted_count} notifications supprimées', 'deleted_count': deleted_count},
                status=status.HTTP_200_OK
            )

        # Bulk delete all notifications for this user (with optional target filter)
        qs = Notification.objects.filter(user=request.user)
        if target:
            qs = qs.filter(target__in=[target, 'both'])
        deleted_count, _ = qs.delete()

        return Response(
            {'message': 'Toutes les notifications ont été supprimées', 'deleted_count': deleted_count},
            status=status.HTTP_200_OK
        )


class DeviceTokenView(APIView):
    """Device FCM Token registration and unregistration"""
    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Register or update device FCM token"""
        token = request.data.get('token')
        device_type = request.data.get('device_type', 'android')

        if not token:
            return Response({'error': 'Token est requis'}, status=status.HTTP_400_BAD_REQUEST)

        device_token, created = DeviceToken.objects.update_or_create(
            token=token,
            defaults={
                'user': request.user,
                'device_type': device_type,
            }
        )

        return Response({
            'message': 'Token FCM enregistré avec succès',
            'created': created
        }, status=status.HTTP_200_OK)

    def delete(self, request):
        """Unregister device token on logout"""
        token = request.data.get('token')
        if token:
            deleted_count, _ = DeviceToken.objects.filter(token=token, user=request.user).delete()
        else:
            deleted_count, _ = DeviceToken.objects.filter(user=request.user).delete()

        return Response({
            'message': f'{deleted_count} token(s) supprimé(s)'
        }, status=status.HTTP_200_OK)



# ============================================================================
# LEADERBOARD & STATS APIs
# ============================================================================

class LeaderboardView(APIView):
    """Leaderboard API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get leaderboard"""
        city = request.query_params.get('city', '')
        club_id = request.query_params.get('club_id', '')
        limit = int(request.query_params.get('limit', 50))

        stats = PlayerStats.objects.select_related('user__profile')

        if city:
            stats = stats.filter(city__icontains=city)

        if club_id:
            # Get players who frequently play at this club
            stats = stats.filter(favorite_club_id=club_id)

        # Order by win rate and matches won
        stats = stats.order_by('-matches_won', '-matches_played')[:limit]

        serializer = PlayerStatsSerializer(stats, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class UserStatsView(APIView):
    """User statistics API"""
    permission_classes = [IsAuthenticated]

    def get(self, request, user_id=None):
        """Get user stats"""
        if user_id:
            try:
                user = User.objects.get(id=user_id)
            except User.DoesNotExist:
                return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)
        else:
            user = request.user

        if hasattr(user, 'stats'):
            serializer = PlayerStatsSerializer(user.stats)
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            return Response({'error': 'Statistiques non trouvées'}, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# USER MANAGEMENT API (Admin Dashboard)
# ============================================================================

class UserListView(APIView):
    """User list and management API for admin dashboard"""
    permission_classes = [IsAdminUserRole]

    def get(self, request):
        """Get all users with profiles"""
        users = User.objects.select_related('profile').all().order_by('-date_joined')
        
        # Search filter
        search = request.query_params.get('search')
        if search:
            search = search.strip()
            users = users.filter(
                Q(username__icontains=search) |
                Q(email__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(profile__full_name__icontains=search)
            )

        # Email filter
        email = request.query_params.get('email')
        if email:
            users = users.filter(email__icontains=email.strip())

        # Status filter
        is_active = request.query_params.get('is_active')
        if is_active in ['true', 'True', '1']:
            users = users.filter(is_active=True)
        elif is_active in ['false', 'False', '0']:
            users = users.filter(is_active=False)

        # Role filtering
        role_filter = request.query_params.get('role')
        if role_filter:
            if role_filter == 'admin':
                users = users.filter(Q(profile__role='admin') | Q(is_staff=True) | Q(is_superuser=True))
            elif role_filter == 'manager':
                users = users.filter(profile__role='manager', is_staff=False, is_superuser=False)
            elif role_filter == 'player':
                users = users.filter(
                    (Q(profile__role='player') | Q(profile__role__isnull=True) | Q(profile__isnull=True)),
                    is_staff=False,
                    is_superuser=False
                )
            else:
                users = users.filter(profile__role=role_filter)
            
        serializer = UserDetailSerializer(users, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Create a new user"""
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            # If profile data is provided, update it
            if 'profile' in request.data and hasattr(user, 'profile'):
                p_data = request.data['profile']
                for field in ['full_name', 'phone_number', 'skill_level', 'evaluation_type']:
                    if field in p_data: setattr(user.profile, field, p_data[field])
                user.profile.save()
            
            return Response(UserDetailSerializer(user).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class UserDetailManagementView(APIView):
    """User detail management API for admin dashboard"""
    permission_classes = [IsAdminUserRole]

    def get(self, request, user_id):
        """Get user details"""
        try:
            user = User.objects.select_related('profile', 'stats').get(id=user_id)
            serializer = UserDetailSerializer(user, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    def put(self, request, user_id):
        return self.patch(request, user_id)

    def patch(self, request, user_id):
        try:
            user = User.objects.get(id=user_id)
            if 'username' in request.data: user.username = request.data['username']
            if 'email' in request.data: user.email = request.data['email']
            if 'first_name' in request.data: user.first_name = request.data['first_name']
            if 'last_name' in request.data: user.last_name = request.data['last_name']
            if 'is_active' in request.data: user.is_active = request.data['is_active']
            if 'is_staff' in request.data: user.is_staff = request.data['is_staff']
            if 'password' in request.data and request.data['password']:
                pwd = request.data['password'].strip() if isinstance(request.data['password'], str) else str(request.data['password'])
                if pwd:
                    if len(pwd) < 6:
                        return Response({'password': ['Le mot de passe doit contenir au moins 6 caractères']}, status=status.HTTP_400_BAD_REQUEST)
                    user.set_password(pwd)
            user.save()

            if 'profile' in request.data and hasattr(user, 'profile'):
                p_data = request.data['profile']
                if 'right-handed' in p_data and 'right_handed' not in p_data:
                    p_data['right_handed'] = p_data['right-handed']
                profile_fields = [
                    'role', 'full_name', 'phone_number', 'skill_level', 'evaluation_type', 
                    'bio', 'location', 'is_verified', 'rating_points', 
                    'tier_level', 'tier_name', 'public_skill_level', 'right_handed'
                ]
                for field in profile_fields:
                    if field in p_data: setattr(user.profile, field, p_data[field])
                user.profile.save()

            if 'stats' in request.data and hasattr(user, 'stats'):
                s_data = request.data['stats']
                stats_fields = ['matches_played', 'matches_won', 'matches_lost', 'total_hours']
                for field in stats_fields:
                    if field in s_data: setattr(user.stats, field, s_data[field])
                user.stats.save()

            serializer = UserDetailSerializer(user, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, user_id):
        """Delete a user"""
        try:
            user = User.objects.get(id=user_id)
            user.delete()
            return Response({'message': 'Utilisateur supprimé avec succès'}, status=status.HTTP_204_NO_CONTENT)
        except User.DoesNotExist:
            return Response({'error': 'Utilisateur non trouvé'}, status=status.HTTP_404_NOT_FOUND)


# ============================================================================
# USER SEARCH API
# ============================================================================

class UserSearchView(APIView):
    """Search users"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Search for users"""
        query = request.query_params.get('q', '').strip()

        if len(query) < 2:
            return Response({'error': 'Requête de recherche trop courte'}, status=status.HTTP_400_BAD_REQUEST)

        # Get blocked user IDs
        blocked_user_ids = BlockedUser.get_blocked_user_ids(request.user)

        search_q = (
            Q(username__icontains=query) |
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(email__icontains=query) |
            Q(full_name_db__icontains=query) |
            Q(reverse_full_name_db__icontains=query)
        )

        words = query.split()
        if len(words) >= 2:
            w1 = words[0]
            w2 = " ".join(words[1:])
            search_q |= (
                (Q(first_name__icontains=w1) & Q(last_name__icontains=w2)) |
                (Q(first_name__icontains=w2) & Q(last_name__icontains=w1))
            )

        users = User.objects.annotate(
            full_name_db=Concat('first_name', Value(' '), 'last_name'),
            reverse_full_name_db=Concat('last_name', Value(' '), 'first_name'),
        ).filter(
            search_q
        ).exclude(
            Q(id=request.user.id) |
            Q(id__in=blocked_user_ids)
        )[:20]

        results = []
        for user in users:
            full_name = f"{user.first_name} {user.last_name}".strip()
            avatar_url = None
            if hasattr(user, 'profile') and user.profile.avatar:
                try:
                    avatar_url = request.build_absolute_uri(user.profile.avatar.url)
                except Exception:
                    avatar_url = user.profile.avatar.url

            results.append({
                'id': user.id,
                'username': user.username,
                'full_name': full_name if full_name else user.username,
                'email': user.email,
                'avatar': avatar_url,
                'skill_level': user.profile.skill_level if hasattr(user, 'profile') else None,
                'evaluation_type': user.profile.evaluation_type if hasattr(user, 'profile') else 'new',
                'is_friend': Friendship.are_friends(request.user, user),
                'has_pending_request': FriendRequest.objects.filter(
                    Q(sender=request.user, receiver=user, status='pending') |
                    Q(sender=user, receiver=request.user, status='pending')
                ).exists()
            })

        return Response(results, status=status.HTTP_200_OK)


# ============================================================================
# SAVED CLUBS API
# ============================================================================

class SavedClubView(APIView):
    """Saved/favorite clubs API"""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Get user's saved clubs"""
        from .models import SavedClub
        from .serializers import SavedClubSerializer

        saved_clubs = SavedClub.objects.filter(user=request.user).order_by('-created_at')
        serializer = SavedClubSerializer(saved_clubs, many=True, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        """Save/favorite a club"""
        from .models import SavedClub
        from .serializers import SavedClubSerializer

        club_id = request.data.get('club_id')

        if not club_id:
            return Response({'error': 'club_id est requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            club = Club.objects.get(id=club_id)
        except Club.DoesNotExist:
            return Response({'error': 'Club non trouvé'}, status=status.HTTP_404_NOT_FOUND)

        # Check if already saved
        saved_club, created = SavedClub.objects.get_or_create(
            user=request.user,
            club=club
        )

        if created:
            serializer = SavedClubSerializer(saved_club, context={'request': request})
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        else:
            return Response({'error': 'Club déjà enregistré'}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        """Unsave/unfavorite a club"""
        from .models import SavedClub

        club_id = request.data.get('club_id')

        if not club_id:
            return Response({'error': 'club_id est requis'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            saved_club = SavedClub.objects.get(user=request.user, club_id=club_id)
            saved_club.delete()
            return Response({'message': 'Club retiré des favoris'}, status=status.HTTP_200_OK)
        except SavedClub.DoesNotExist:
            return Response({'error': 'Club non enregistré dans les favoris'}, status=status.HTTP_404_NOT_FOUND)