from django.contrib import admin

from .models import *


# Register your models here.
@admin.register(MySite)
class MySiteAdmin(admin.ModelAdmin):
    pass
