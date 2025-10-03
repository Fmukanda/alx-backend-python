from django.apps import AppConfig


class MessagingApp1Config(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'messaging_app1'
   
    def ready(self):
        # Import signals when the app is ready
        import your_app_name.signals
        import your_app_name.user_signals  
