from django.conf import settings


def google_client_id(request):
    """Make GOOGLE_CLIENT_ID available to all templates"""
    return {
        'google_client_id': getattr(settings, 'GOOGLE_CLIENT_ID', ''),
    }
