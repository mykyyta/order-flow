from django.contrib.auth.decorators import login_required
from django.shortcuts import render


@login_required
def palette_lab(request):
    return render(
        request,
        "orders/palette_lab.html",
        {
            "page_title": "Палітра",
        },
    )

