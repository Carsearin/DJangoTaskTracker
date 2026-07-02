from django.urls import path

from tasks.views import tasks_list

urlpatterns = [
    path("", tasks_list, name="tasks-list"),
]