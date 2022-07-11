import shutil
import tempfile

from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from django.conf import settings
from django.core.cache import cache

from ..models import Post, Group, User, Comment, Follow
from ..settings import POSTS_PER_PAGE

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
SLUG_OF_GROUP = 'test_slug'
SLUG_OF_GROUP_2 = 'test_slug2'
USERNAME = 'TEST'
USERNAME_2 = 'TEST2'
USERNAME_3 = 'TEST3'
URL_OF_INDEX = reverse('posts:index')
URL_OF_POSTS_OF_GROUP = reverse('posts:group_list', args=[SLUG_OF_GROUP])
URL_OF_POSTS_OF_GROUP_2 = reverse('posts:group_list', args=[SLUG_OF_GROUP_2])
URL_TO_CREATE_POST = reverse('posts:post_create')
URL_OF_PROFILE = reverse('posts:profile', args=[USERNAME])
URL_OF_INDEX_FOLLOW = reverse('posts:follow_index')
URL_OF_FOLLOW = reverse('posts:profile_follow', args=[USERNAME_2])
URL_OF_UNFOLLOW = reverse('posts:profile_unfollow', args=[USERNAME_2])
small_gif = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostPagesTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        cls.user = User.objects.create_user(username=USERNAME)
        cls.user_2 = User.objects.create_user(username=USERNAME_2)
        cls.user_3 = User.objects.create_user(username=USERNAME_3)
        cls.group_2 = Group.objects.create(
            title='Заголовок 2',
            slug=SLUG_OF_GROUP_2
        )
        cls.group = Group.objects.create(
            title='Заголовок 1',
            slug=SLUG_OF_GROUP
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый текст',
            group=cls.group,
            image=cls.uploaded
        )
        cls.comment = Comment.objects.create(
            author=cls.user,
            text='Тестовый комментарий',
            post=cls.post,
        )
        cls.URL_OF_DETAIL_POST = reverse(
            'posts:post_detail',
            args=[cls.post.pk]
        )
        cls.follow = Follow.objects.create(
            author=cls.user,
            user=cls.user_2,
        )
        cls.URL_TO_EDIT_POST = reverse('posts:post_edit', args=[cls.post.pk])
        cls.URL_TO_CREATE_COMMENT = reverse(
            'posts:add_comment',
            args=[cls.post.pk]
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.guest_client = Client()
        self.authorized_client = Client()
        self.another = Client()
        self.another_2 = Client()
        self.authorized_client.force_login(self.user)
        self.another.force_login(self.user_2)
        self.another_2.force_login(self.user_3)

    def test_pages_show_correct_context(self):
        """Шаблон сформирован с правильным контекстом."""
        cases = [
            [URL_OF_INDEX, 'page_obj'],
            [URL_OF_POSTS_OF_GROUP, 'page_obj'],
            [URL_OF_PROFILE, 'page_obj'],
            [self.URL_OF_DETAIL_POST, 'post'],
        ]
        for url, key in cases:
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                obj = response.context.get(key)
                if key == 'page_obj':
                    self.assertEqual(len(obj), 1)
                    post = obj[0]
                else:
                    post = obj
                self.assertEqual(self.post.text, post.text)
                self.assertEqual(self.post.author, post.author)
                self.assertEqual(self.post.group, post.group)
                self.assertEqual(self.post.pk, post.pk)

    def test_group_pages_correct_context(self):
        """Шаблон group_pages сформирован с правильным контекстом."""
        response = self.authorized_client.get(URL_OF_POSTS_OF_GROUP)
        group = response.context['group']
        self.assertEqual(group.title, self.group.title)
        self.assertEqual(group.slug, self.group.slug)
        self.assertEqual(group.pk, self.group.pk)
        self.assertEqual(group.posts, self.group.posts)

    def test_post_another_group(self):
        """Пост не попал в другую группу"""
        response = self.authorized_client.get(URL_OF_POSTS_OF_GROUP_2)
        self.assertNotIn(self.post, response.context['page_obj'])

    def test_author_in_profile(self):
        response = self.guest_client.get(URL_OF_PROFILE)
        self.assertEqual(self.user, response.context['author'])

    def test_context(self):
        cases = [
            [URL_OF_INDEX, 'page_obj'],
            [URL_OF_POSTS_OF_GROUP, 'page_obj'],
            [URL_OF_PROFILE, 'page_obj'],
            [self.URL_OF_DETAIL_POST, 'post'],
        ]
        for url, context in cases:
            with self.subTest(url=url):
                post = self.guest_client.get(url).context[context]
                if context == 'page_obj':
                    self.assertEqual(len(post), 1)
                    post = post[0]
                self.assertEqual(post.text, self.post.text)
                self.assertEqual(post.group, self.post.group)
                self.assertEqual(post.author, self.post.author)
                self.assertEqual(post.image, self.post.image)

    def test_comment_form(self):
        response = self.guest_client.get(self.URL_TO_CREATE_COMMENT)
        self.assertEqual(response.status_code, 302)

    def test_comment_in_page_of_post(self):
        response = self.authorized_client.get(self.URL_OF_DETAIL_POST)
        comment = response.context['comments'][0]
        self.assertEqual(comment.text, self.comment.text)
        self.assertEqual(comment.author, self.comment.author)
        self.assertEqual(comment.post, self.comment.post)

    def test_caching_page_of_index(self):
        response = self.guest_client.get(URL_OF_INDEX)
        Post.objects.filter(text='Тестовый текст').delete()
        response_2 = self.guest_client.get(URL_OF_INDEX)
        self.assertEqual(response.content, response_2.content)
        cache.clear()
        response_3 = self.guest_client.get(URL_OF_INDEX)
        self.assertNotEqual(response.content, response_3.content)

    def test_following_and_unfollowing(self):
        self.assertEqual(
            Follow.objects.filter(user=self.user)[0].user,
            self.user
        )
        self.assertEqual(
            Follow.objects.filter(author=self.user_2)[0].author,
            self.user_2
        )
        self.assertFalse(Follow.objects.filter(
            user=self.user,
            author=self.user_2).exists()
                         )

    def test_new_post_after_following(self):
        new_post = Post.objects.create(
            author=self.user,
            text='Тестовый text',
            group=self.group,
        )
        response = self.another.get(URL_OF_INDEX_FOLLOW)
        response_2 = self.another_2.get(URL_OF_INDEX_FOLLOW)
        self.assertIn(new_post, response.context['page_obj'])
        self.assertNotIn(new_post, response_2.context['posts_of_authors'])


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username=USERNAME)
        cls.group = Group.objects.create(
            title='Test group',
            slug=SLUG_OF_GROUP,
            description='Тестовое описание',
        )
        Post.objects.bulk_create(Post(
            text=f'Тестовый пост {number}',
            author=cls.user,
            group=cls.group)
            for number in range(POSTS_PER_PAGE + 1))

    def setUp(self):
        self.guest_client = Client()

    def test_paginator(self):
        self.urls = {
            URL_OF_INDEX: POSTS_PER_PAGE,
            URL_OF_POSTS_OF_GROUP: POSTS_PER_PAGE,
            URL_OF_PROFILE: POSTS_PER_PAGE,
            URL_OF_INDEX + "?page=2": 1,
            URL_OF_POSTS_OF_GROUP + "?page=2": 1,
            URL_OF_PROFILE + "?page=2": 1
        }

        for url, post_count in self.urls.items():
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(
                    len(response.context.get('page_obj')), post_count
                )
