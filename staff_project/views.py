from django.shortcuts import render, redirect
from django.contrib.auth import logout

def home(request):
    return render(request, 'staff/home.html')  # this will work once you make the file

def logout_view(request):
    logout(request)
    return redirect('staff:staff_login')