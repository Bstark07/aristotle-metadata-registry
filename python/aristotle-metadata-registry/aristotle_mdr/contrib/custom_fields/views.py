from django.urls import reverse
from django.views.generic import CreateView, UpdateView, DeleteView, ListView
from django.contrib.auth.mixins import LoginRequiredMixin

from aristotle_mdr.mixins import IsSuperUserMixin
from aristotle_mdr.contrib.custom_fields import models


class CustomFieldCreateView(IsSuperUserMixin, CreateView):
    model=models.CustomField
    fields='__all__'
    template_name='aristotle_mdr/custom_fields/field_form.html'

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['heading'] = 'Create Custom Field'
        context['submit_text'] = 'Create'
        return context

    def get_success_url(self):
        return reverse('aristotle_mdr:userAdminTools')


class CustomFieldUpdateView(IsSuperUserMixin, UpdateView):
    model=models.CustomField
    fields='__all__'
    template_name='aristotle_mdr/custom_fields/field_form.html'

    def get_success_url(self):
        return reverse('aristotle_mdr:userAdminTools')

    def get_context_data(self, *args, **kwargs):
        context = super().get_context_data(*args, **kwargs)
        context['heading'] = 'Update Custom Field'
        context['submit_text'] = 'Update'
        return context


class CustomFieldDeleteView(IsSuperUserMixin, DeleteView):
    model=models.CustomField
    template_name='aristotle_mdr/custom_fields/delete.html'

    def get_success_url(self):
        return reverse('aristotle_mdr:userAdminTools')


class CustomFieldListView(IsSuperUserMixin, ListView):
    queryset=models.CustomField.objects.all()
    template_name='aristotle_mdr/custom_fields/list.html'

    def get_success_url(self):
        return reverse('aristotle_mdr:userAdminTools')
