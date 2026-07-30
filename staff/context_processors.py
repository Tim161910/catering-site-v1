def notifications(request):
    if request.user.is_authenticated:
        unread_count = request.user.notifications.filter(is_read=False).count()
        recent_notifications = request.user.notifications.order_by('-created_at')[:5]
        return {
            'unread_notification_count': unread_count,
            'notifications': recent_notifications
        }
    return {}