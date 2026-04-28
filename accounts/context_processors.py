from .models import PrivateMessage, SessionRequest


def navbar_notifications(request):
    if not request.user.is_authenticated:
        return {}

    unread_message_count = PrivateMessage.objects.filter(
        receiver=request.user,
        is_read=False,
    ).count()
    pending_request_count = SessionRequest.objects.filter(
        skill__owner=request.user,
        status=SessionRequest.STATUS_PENDING,
    ).count()

    return {
        'navbar_unread_message_count': unread_message_count,
        'navbar_pending_request_count': pending_request_count,
    }
