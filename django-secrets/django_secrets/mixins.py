from django.conf import settings
from django.utils.translation import gettext_lazy as _
from django.http import Http404
from .utils import decode_id


class KnuthIdMixin(object):
    """Mixin for views that use encoded UUID IDs in URLs"""
    knuth_id_url_kwarg = 'oid'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        oid = self.kwargs.get(self.knuth_id_url_kwarg, None)

        if oid is None:
            raise AttributeError("Generic detail view %s must be called with "
                                 "an object oid."
                                 % self.__class__.__name__)

        # Decode the base64-encoded UUID
        pk = decode_id(oid)

        if pk is None:
            raise Http404(_("Invalid secret ID"))

        queryset = queryset.filter(pk=pk)

        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj
