from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .forms import RegisterForm


def register(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect('login')

    else:
        form = RegisterForm()

    return render(request, 'accounts/register.html', {
        'form': form
    })


@login_required
def profile(request):
    return render(request, 'accounts/profile.html')
# Create your views here.
