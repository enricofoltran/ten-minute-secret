from django.views.generic.edit import CreateView, UpdateView
from django.shortcuts import render_to_response
from django.views.decorators.cache import never_cache
from .forms import SecretCreateForm, SecretUpdateForm
from .mixins import KnuthIdMixin
from .models import Secret


class SecretCreateView(CreateView):
    model = Secret
    form_class = SecretCreateForm
    template_name_suffix = '_create'


class SecretUpdateView(KnuthIdMixin, UpdateView):
    model = Secret
    queryset = Secret.available
    form_class = SecretUpdateForm
    template_name_suffix = '_update'

    @classmethod
    def as_view(cls, **initkwargs):
        view = super(SecretUpdateView, cls).as_view(**initkwargs)
        return never_cache(view)

    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.views += 1
        self.object.save()

        return render_to_response('secrets/secret_detail.html', {
            "request": self.request,
            "object":  self.object,
        })
