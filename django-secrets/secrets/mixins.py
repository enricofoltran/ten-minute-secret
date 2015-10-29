from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from django.http import Http404
from .utils import knuth_decode


class KnuthIdMixin(object):
    knuth_id_url_kwarg = 'oid'

    def get_object(self, queryset=None):
        if queryset is None:
            queryset = self.get_queryset()

        oid = self.kwargs.get(self.knuth_id_url_kwarg, None)

        if oid is None:
            raise AttributeError("Generic detail view %s must be called with "
                                 "an object oid."
                                 % self.__class__.__name__)

        pk = knuth_decode(oid)
        queryset = queryset.filter(pk=pk)

        try:
            obj = queryset.get()
        except queryset.model.DoesNotExist:
            raise Http404(_("No %(verbose_name)s found matching the query") %
                          {'verbose_name': queryset.model._meta.verbose_name})
        return obj
