from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User
from .models import (
    Profile, Club, Court, Booking, Match, MatchParticipant, MatchMessage,
    Rating, CourtRating, Notification, PlayerStats, CommunityPost, PostReply,
    CommunityGroup, FriendRequest, Friendship, PrivateMessage, BlockedUser, SavedClub
)


# Define an inline admin descriptor for Profile model
class ProfileInline(admin.StackedInline):
    model = Profile
    can_delete = False
    verbose_name_plural = 'Profile'


# Define a new User admin
class UserAdmin(UserAdmin):
    inlines = (ProfileInline, )


# Re-register UserAdmin
admin.site.unregister(User)
admin.site.register(User, UserAdmin)


# Custom admin classes for better display
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'skill_level', 'public_skill_level', 'total_skill_ratings']
    list_filter = ['skill_level']
    search_fields = ['user__username', 'user__email', 'full_name']


@admin.register(Club)
class ClubAdmin(admin.ModelAdmin):
    list_display = ['name', 'city', 'postal_code', 'rating', 'is_partner']
    list_filter = ['city', 'is_partner', 'rating']
    search_fields = ['name', 'city', 'postal_code', 'address']


@admin.register(Court)
class CourtAdmin(admin.ModelAdmin):
    list_display = ['name', 'club', 'is_indoor', 'price_per_hour', 'is_available']
    list_filter = ['club', 'is_indoor', 'is_available']
    search_fields = ['name', 'club__name']


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'court', 'date', 'start_time', 'end_time', 'status']
    list_filter = ['status', 'date', 'court__club']
    search_fields = ['user__username', 'court__name']
    date_hierarchy = 'date'


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = ['title', 'organizer', 'club', 'court', 'date_time', 'match_type', 'status', 'is_open', 'created_at']
    list_filter = ['match_type', 'status', 'is_open', 'created_at', 'club']
    search_fields = ['title', 'organizer__username', 'club__name', 'court__name', 'share_code']
    date_hierarchy = 'created_at'


@admin.register(MatchParticipant)
class MatchParticipantAdmin(admin.ModelAdmin):
    list_display = ['match', 'user', 'status', 'joined_at']
    list_filter = ['status', 'joined_at']
    search_fields = ['user__username', 'match__id']


@admin.register(MatchMessage)
class MatchMessageAdmin(admin.ModelAdmin):
    list_display = ['match', 'sender', 'content', 'created_at']
    list_filter = ['created_at']
    search_fields = ['sender__username', 'content']
    date_hierarchy = 'created_at'


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ['rater', 'rated_user', 'match', 'rating', 'created_at']
    list_filter = ['created_at', 'rating']
    search_fields = ['rater__username', 'rated_user__username']
    date_hierarchy = 'created_at'


@admin.register(CourtRating)
class CourtRatingAdmin(admin.ModelAdmin):
    list_display = ['court', 'rater', 'match', 'rating', 'created_at']
    list_filter = ['created_at', 'rating']
    search_fields = ['rater__username', 'court__name']
    date_hierarchy = 'created_at'


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'type', 'is_read', 'created_at']
    list_filter = ['type', 'is_read', 'created_at']
    search_fields = ['user__username', 'message']
    date_hierarchy = 'created_at'


@admin.register(PlayerStats)
class PlayerStatsAdmin(admin.ModelAdmin):
    list_display = ['user', 'matches_played', 'matches_won', 'matches_lost', 'win_rate']
    list_filter = ['matches_played']
    search_fields = ['user__username']
    
    def win_rate(self, obj):
        if obj.matches_played > 0:
            return f"{(obj.matches_won / obj.matches_played * 100):.1f}%"
        return "0%"
    win_rate.short_description = 'Win Rate'


@admin.register(CommunityPost)
class CommunityPostAdmin(admin.ModelAdmin):
    list_display = ['author', 'title', 'category', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['author__username', 'title', 'content']
    date_hierarchy = 'created_at'


@admin.register(CommunityGroup)
class CommunityGroupAdmin(admin.ModelAdmin):
    list_display = ['name', 'creator', 'city', 'is_public', 'created_at']
    list_filter = ['is_public', 'city', 'created_at']
    search_fields = ['name', 'description', 'city']
    filter_horizontal = ['members']


@admin.register(FriendRequest)
class FriendRequestAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['sender__username', 'receiver__username']
    date_hierarchy = 'created_at'


@admin.register(Friendship)
class FriendshipAdmin(admin.ModelAdmin):
    list_display = ['user1', 'user2', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user1__username', 'user2__username']
    date_hierarchy = 'created_at'


@admin.register(PrivateMessage)
class PrivateMessageAdmin(admin.ModelAdmin):
    list_display = ['sender', 'receiver', 'is_read', 'created_at']
    list_filter = ['is_read', 'created_at']
    search_fields = ['sender__username', 'receiver__username', 'content']
    date_hierarchy = 'created_at'


@admin.register(BlockedUser)
class BlockedUserAdmin(admin.ModelAdmin):
    list_display = ['blocker', 'blocked', 'created_at']
    list_filter = ['created_at']
    search_fields = ['blocker__username', 'blocked__username', 'reason']
    date_hierarchy = 'created_at'


@admin.register(SavedClub)
class SavedClubAdmin(admin.ModelAdmin):
    list_display = ['user', 'club', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'club__name']
    date_hierarchy = 'created_at'