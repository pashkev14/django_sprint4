from django.shortcuts import render, get_object_or_404, redirect
from .models import Post, Category, Comment
from django.contrib.auth.models import User
from datetime import datetime
from django.core.paginator import Paginator
from django.views.generic import (
    DetailView, UpdateView, ListView, CreateView, DeleteView
)
from .forms import UserProfileForm, PostForm, CommentForm
from django.urls import reverse_lazy, reverse
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import Http404
from django.utils import timezone
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.db.models import Count


class CommentDeleteView(LoginRequiredMixin, DeleteView):
    model = Comment
    template_name = 'blog/comment.html'
    pk_url_kwarg = 'comment_id'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        val_1 = self.request.user.is_authenticated
        val_2 = self.object.author == self.request.user
        if not (val_1 and val_2):
            return redirect(reverse(
                'blog:post_detail', kwargs={'post_id': self.object.pk}
            ))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        post_id = self.kwargs.get('post_id')
        return reverse_lazy('blog:post_detail', kwargs={'post_id': post_id})


class CommentUpdateView(LoginRequiredMixin, UpdateView):
    post_com = None
    model = Comment
    form_class = CommentForm
    template_name = 'blog/comment.html'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        val_1 = self.request.user.is_authenticated
        val_2 = self.object.author == self.request.user
        if not (val_1 and val_2):
            return redirect(reverse(
                'blog:post_detail',
                kwargs={'post_id': self.kwargs.get('post_id')}
            ))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        comment_id = self.kwargs.get('comment_id')
        return get_object_or_404(Comment, id=comment_id)

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs.get('post_id')}
        )


class CommentCreateView(LoginRequiredMixin, CreateView):
    model = Comment
    form_class = CommentForm
    template_name = 'comments.html'

    def form_valid(self, form):
        post = get_object_or_404(Post, pk=self.kwargs.get('post_id'))
        form.instance.author = self.request.user
        form.instance.post = post
        return super().form_valid(form)

    def get_success_url(self):
        return reverse(
            'blog:post_detail',
            kwargs={'post_id': self.kwargs.get('post_id')}
        )


class PostDeleteView(LoginRequiredMixin, DeleteView):
    model = Post
    success_url = reverse_lazy('blog:index')
    template_name = 'blog/create.html'
    success_url = reverse_lazy('blog:index')
    pk_url_kwarg = 'post_id'

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        val_1 = self.request.user.is_authenticated
        val_2 = self.object.author == self.request.user
        if not (val_1 and val_2):
            return redirect(reverse(
                'blog:post_detail', kwargs={'post_id': self.object.pk}
            ))
        else:
            return super().dispatch(request, *args, **kwargs)


class PostUpdateView(UpdateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def get_object(self, queryset=None):
        post_id = self.kwargs.get('post_id')
        return get_object_or_404(Post, id=post_id)

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        val_1 = self.request.user.is_authenticated
        val_2 = self.object.author == self.request.user
        if not (val_1 and val_2):
            return redirect(reverse(
                'blog:post_detail', kwargs={'post_id': self.object.pk}
            ))
        else:
            return super().dispatch(request, *args, **kwargs)

    def get_success_url(self):
        return reverse_lazy(
            'blog:post_detail', kwargs={'post_id': self.object.pk}
        )


@method_decorator(login_required(
    login_url=reverse_lazy('login')
), name='dispatch')
class PostCreateView(CreateView):
    model = Post
    form_class = PostForm
    template_name = 'blog/create.html'

    def form_valid(self, form):
        form.instance.author = self.request.user
        return super().form_valid(form)

    def get_success_url(self):
        username = self.object.author.username
        return reverse('blog:profile', args=[username])


@method_decorator(login_required(
    login_url=reverse_lazy('login')
), name='dispatch')
class ProfileUpdateView(UpdateView):
    model = User
    form_class = UserProfileForm
    template_name = 'blog/user.html'

    def get_success_url(self):
        return reverse_lazy(
            'blog:profile', kwargs={'username': self.object.username}
        )

    def get_object(self):
        return self.request.user


class ProfileListView(ListView):
    model = Post
    template_name = 'blog/profile.html'
    paginate_by = 10

    def get_queryset(self):
        username = self.kwargs['username']
        profile = get_object_or_404(User, username=username)
        posts = Post.objects.filter(author=profile).select_related(
            'author').prefetch_related('comments', 'category', 'location')
        posts_annotated = posts.annotate(comment_count=Count('comments'))
        return posts_annotated.order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        if 'profile' not in context:
            context['profile'] = get_object_or_404(
                User, username=self.kwargs['username'])
        return context


class PostListView(ListView):
    template_name = 'blog/index.html'
    model = Post
    queryset = Post.objects.prefetch_related(
        'category',
        'location',
    ).select_related('author').filter(
        pub_date__lte=datetime.now(),
        is_published=True,
        category__is_published=True
    ).annotate(comment_count=Count('comments')).order_by('-pub_date')
    paginate_by = 10


class PostDetailView(DetailView):
    model = Post
    template_name = 'blog/detail.html'

    def get_object(self, queryset=None):
        post_id = self.kwargs.get('post_id')
        post = get_object_or_404(Post, id=post_id)
        if (
            post.author == self.request.user
            or (post.is_published and post.category.is_published
                and post.pub_date <= timezone.now())
        ):
            return post
        raise Http404('Страница не найдена')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        post = self.get_object()
        comments = post.comments.all().order_by('created_at')
        context['form'] = CommentForm()
        context['comments'] = comments

        return context


def category_posts(request, category_slug):
    template = 'blog/category.html'
    category = get_object_or_404(
        Category.objects
        .filter(is_published=True,),
        slug=category_slug
    )
    post_list = Post.objects.prefetch_related(
        'category',
        'location',
    ).select_related('author').filter(
        pub_date__lte=datetime.now(),
        is_published=True,
        category__is_published=True,
        category__slug=category_slug,
    ).order_by('-pub_date')
    paginator = Paginator(post_list, 10)
    page_number = request.GET.get('page')
    posts = paginator.get_page(page_number)
    context = {
        'category': category,
        'page_obj': posts,
    }
    return render(request, template, context)
