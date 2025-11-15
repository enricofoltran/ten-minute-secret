import datetime
from django.views.generic.edit import CreateView, UpdateView
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.utils import timezone
from django.http import Http404
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator
from .forms import SecretCreateForm, SecretUpdateForm
from .mixins import KnuthIdMixin
from .models import Secret


@method_decorator(ratelimit(key='ip', rate='10/h', method='POST'), name='post')
class SecretCreateView(CreateView):
    model = Secret
    form_class = SecretCreateForm
    template_name_suffix = '_create'


@method_decorator(ratelimit(key='ip', rate='20/h', method='POST'), name='post')
class SecretUpdateView(KnuthIdMixin, UpdateView):
    model = Secret
    queryset = Secret.available
    form_class = SecretUpdateForm
    template_name_suffix = '_update'

    @classmethod
    def as_view(cls, **kwargs):
        view = super(SecretUpdateView, cls).as_view(**kwargs)
        return never_cache(view)

    def form_valid(self, form):
        self.object = form.save(commit=False)

        # SECURITY: Double-check expiration before displaying
        now = timezone.now()
        threshold = now - datetime.timedelta(minutes=10)
        if self.object.created_at < threshold:
            self.object.delete()
            raise Http404("This secret has expired")

        # Delete the secret after successful retrieval
        self.object.delete()

        return render(self.request, 'django_secrets/secret_detail.html', {
            "object": self.object,
        })
