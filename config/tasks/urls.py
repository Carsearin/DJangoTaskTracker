from django.urls import path

from tasks.views import task_detail, tasks_list


urlpatterns = [
    path("", tasks_list, name="tasks-list"),
    path("<int:task_id>", task_detail, name="task-detail"),
]