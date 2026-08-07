from django.urls import reverse_lazy

class EventsAdminSiteMixin:
    def get_app_list(self, request):
        app_dict = {}
        EVENT_MODELS = {'Event', 'EventTemplate', 'Assignment'} # Assignment added here
        first_event_url = ''

        for model, model_admin in self._registry.items():
            has_perm = True
            model_name = model._meta.model_name
            app_label = model._meta.app_label # <- THIS is the fix

            # Use app_label, not hardcoded 'staff'
            real_admin_url = reverse_lazy(f'{self.name}:{app_label}_{model_name}_changelist')
            real_add_url = reverse_lazy(f'{self.name}:{app_label}_{model_name}_add')

            if model._meta.object_name in EVENT_MODELS and not first_event_url:
                first_event_url = real_admin_url 

            if model._meta.object_name in EVENT_MODELS:
                admin_url = real_admin_url
                add_url = real_add_url
                app_key = 'events'
                app_name = 'Events'
            else:
                admin_url = real_admin_url
                add_url = real_add_url
                app_key = 'staff'
                app_name = 'Staff'

            defaults = {
                'model': model,
                'name': model._meta.verbose_name_plural.title(),
                'object_name': model._meta.object_name,
                'perms': {'view': has_perm, 'change': has_perm, 'add': has_perm, 'delete': has_perm},
                'admin_url': admin_url,
                'add_url': add_url,
            }

            if app_key not in app_dict:
                app_dict[app_key] = {
                    'name': app_name,
                    'app_label': app_key,
                    'app_url': first_event_url,
                    'models': []
                }
            app_dict[app_key]['models'].append(defaults)

        result = []
        if 'events' in app_dict: result.append(app_dict['events'])
        if 'staff' in app_dict: result.append(app_dict['staff'])
        return result