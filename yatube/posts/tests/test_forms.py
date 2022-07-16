import shutil
import tempfile

from django import forms
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from ..models import Post, Group, User, Comment

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)
SLUG_OF_GROUP = 'test_slug'
SLUG_OF_GROUP_2 = 'test_slug2'
URL_TO_CREATE_POST = reverse('posts:post_create')
URL_OF_PROFILE = reverse('posts:profile', args=['test'])
URL_OF_POSTS_OF_GROUP = reverse('posts:group_list', args=[SLUG_OF_GROUP])
URL_OF_INDEX = reverse('posts:index')
URL_NEXT = '?next='
LOGIN_URL = reverse('login')
LOGIN_URL_CREATE = f'{LOGIN_URL}{URL_NEXT}{URL_TO_CREATE_POST}'
SMALL_GIF = (
    b'\x47\x49\x46\x38\x39\x61\x02\x00'
    b'\x01\x00\x80\x00\x00\x00\x00\x00'
    b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
    b'\x00\x00\x00\x2C\x00\x00\x00\x00'
    b'\x02\x00\x01\x00\x00\x02\x02\x0C'
    b'\x0A\x00\x3B'
)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class TaskCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.uploaded = SimpleUploadedFile(
            name='img.gif',
            content=SMALL_GIF,
            content_type='posts/img.gif'
        )
        cls.uploaded_2 = SimpleUploadedFile(
            name='img2.gif',
            content=SMALL_GIF,
            content_type='posts/img2.gif'
        )
        cls.user = User.objects.create_user(username='test')
        cls.group = Group.objects.create(
            title='Test group',
            slug=SLUG_OF_GROUP,
            description='Тестовое описание',
        )
        cls.group_2 = Group.objects.create(
            title='Test group2',
            slug=SLUG_OF_GROUP_2,
            description='Тестовое описание2',
        )
        cls.post = Post.objects.create(
            author=cls.user,
            text='Тестовый пост')
        cls.post_2 = Post.objects.create(
            author=cls.user,
            text='Тестовый пост77')
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='Тестовый комментарий111111')
        cls.URL_OF_DETAIL_POST = reverse(
            'posts:post_detail',
            args=[cls.post.pk]
        )
        cls.URL_TO_ADD_COMMENT = reverse(
            'posts:add_comment',
            args=[cls.post.pk]
        )
        cls.URL_TO_EDIT_POST = reverse('posts:post_edit', args=[cls.post.pk])
        cls.guest_client = Client()
        cls.authorized_client = Client()
        cls.authorized_client.force_login(cls.user)

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def test_create_post(self):
        post_all = set(Post.objects.all())
        form_data = {
            'text': 'Текст12345',
            'group': self.group.id,
            'image': self.uploaded
        }
        response = self.authorized_client.post(
            URL_TO_CREATE_POST, data=form_data, follow=True
        )
        post_all_with_new_post = set(Post.objects.all())
        posts_obj = post_all_with_new_post.difference(post_all)
        self.assertEqual(len(posts_obj), 1)
        new_post = posts_obj.pop()
        self.assertRedirects(response, URL_OF_PROFILE)
        self.assertEqual(new_post.text, form_data['text'])
        self.assertEqual(new_post.group.id, form_data['group'])
        self.assertEqual(new_post.image.name, form_data['image'].content_type)
        self.assertEqual(new_post.author, self.user)

    def test_edit_post(self):
        form_data = {
            'text': 'Измененный пост',
            'group': self.group_2.id,
            'image': self.uploaded_2
        }
        response_edit = self.authorized_client.post(
            self.URL_TO_EDIT_POST, data=form_data, follow=True
        )
        post = response_edit.context['post']
        self.assertEqual(post.text, form_data['text'])
        self.assertEqual(post.group.id, form_data['group'])
        self.assertEqual(post.image.name, form_data['image'].content_type)
        self.assertEqual(post.author, self.post.author)
        self.assertRedirects(response_edit, self.URL_OF_DETAIL_POST)

    def test_post_edit_correct_context(self):
        """Шаблон post_edit и post_create
          сформированы с правильными контекстами."""
        self.URLS_LIST = [self.URL_TO_EDIT_POST, URL_TO_CREATE_POST]
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField,
            'image': forms.fields.ImageField
        }
        for url in self.URLS_LIST:
            response = self.authorized_client.get(url)
            for value, expected in form_fields.items():
                with self.subTest(value=value):
                    form_field = response.context.get('form').fields.get(value)
                    self.assertIsInstance(form_field, expected)

    def test_create_comment(self):
        comment_all = set(self.post.comments.all())
        form_data = {
            'text': 'Комментарий123',
        }
        response = self.authorized_client.post(
            self.URL_TO_ADD_COMMENT, data=form_data, follow=True
        )
        comment_all_with_new_comment = set(self.post.comments.all())
        comments_obj = comment_all_with_new_comment.difference(comment_all)
        self.assertEqual(len(comments_obj), 1)
        new_comment = comments_obj.pop()
        self.assertRedirects(response, self.URL_OF_DETAIL_POST)
        self.assertEqual(new_comment.text, form_data['text'])
        self.assertEqual(new_comment.author, self.user)
        self.assertEqual(new_comment.post.pk, self.post.pk)

