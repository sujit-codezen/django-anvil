from django.contrib import admin
from django.contrib.auth.admin import GroupAdmin

from .models import Role

admin.site.register(Role, GroupAdmin)
