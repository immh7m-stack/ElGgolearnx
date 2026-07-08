from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def elgoplan_home(request):
    return render(request, "planner/elgoplan.html")
