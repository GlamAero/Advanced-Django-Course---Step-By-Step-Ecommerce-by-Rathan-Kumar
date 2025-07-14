from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .models import Review, ReviewVote, ReviewFlag, ReviewImage
from .forms import ReviewForm, ReviewVoteForm, ReviewFlagForm

@login_required
@require_POST
def submit_review(request, product_id):
    form = ReviewForm(request.POST, request.FILES)
    if form.is_valid():
        review = form.save(commit=False)
        review.product_id = product_id
        review.user = request.user
        review.save()

        for image_file in request.FILES.getlist('images'):
            ReviewImage.objects.create(review=review, image=image_file)

        messages.success(request, "Your review has been submitted and is pending moderation.")
    else:
        messages.error(request, "There was an error submitting your review.")
    return redirect('product_detail', slug=review.product.slug)

@login_required
@require_POST
def vote_review(request, review_id):
    form = ReviewVoteForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': 'Invalid form data'}, status=400)

    review = get_object_or_404(Review, id=review_id, is_approved=True)
    vote_type = form.cleaned_data['vote_type']

    vote, created = ReviewVote.objects.get_or_create(user=request.user, review=review)
    vote.vote_type = vote_type
    vote.save()

    upvotes = review.votes.filter(vote_type='up').count()
    downvotes = review.votes.filter(vote_type='down').count()

    return JsonResponse({'upvotes': upvotes, 'downvotes': downvotes})

@login_required
@require_POST
def flag_review(request, review_id):
    form = ReviewFlagForm(request.POST)
    if not form.is_valid():
        return JsonResponse({'error': 'Invalid flag details'}, status=400)

    review = get_object_or_404(Review, id=review_id)
    ReviewFlag.objects.create(
        user=request.user,
        review=review,
        reason=form.cleaned_data['reason'],
        details=form.cleaned_data.get('details')
    )
    return JsonResponse({'message': 'Thank you. We will review this content shortly.'})

@login_required
def moderation_dashboard(request):
    if not request.user.is_staff:
        return HttpResponseBadRequest("Not authorized")

    pending_reviews = Review.objects.filter(is_approved=False).select_related('product', 'user')
    return render(request, 'reviews/moderation_dashboard.html', {'pending_reviews': pending_reviews})