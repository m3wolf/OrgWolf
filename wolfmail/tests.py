"""
This file demonstrates writing tests using the unittest module. These will pass
when you run "manage.py test".

Replace this with more appropriate tests for your application.
"""

import datetime as dt
import json
import pytz

from django.core.urlresolvers import reverse
from django.test import TestCase
from django.utils.timezone import get_current_timezone

from gtd.models import Node
from orgwolf.models import OrgWolfUser as User
from wolfmail.models import Message
from wolfmail.serializers import InboxSerializer, MessageSerializer


class MessageAPI(TestCase):
    fixtures = ['test-users.json', 'messages-test.json',
                'gtd-env.json', 'gtd-test.json']
    def setUp(self):
        self.user = User.objects.get(pk=1)
        self.assertTrue(
            self.client.login(username=self.user.username,
                              password='secret'),
            'Login failed'
        )
        self.url = reverse('messages')

    def test_get_all_messages(self):
        response = self.client.get(self.url)
        r = json.loads(response.content)
        expected = Message.objects.filter(owner=self.user)
        self.assertQuerysetEqual(
            expected,
            [x['subject'] for x in r],
            transform=lambda x: x.subject,
            ordered=False,
        )

    def test_get_inbox(self):
        response = self.client.get(self.url, {'in_inbox': True})
        r = json.loads(response.content)
        expected = Message.objects.filter(owner=self.user, in_inbox=True)
        self.assertQuerysetEqual(
            expected,
            [x['subject'] for x in r],
            transform=lambda x: x.subject,
            ordered=False,
        )

    def test_get_inbox_anonymous(self):
        self.client.logout()
        response = self.client.get(self.url, {'in_inbox': True})
        self.assertEqual(
            response.status_code,
            200
        )
        r = json.loads(response.content)
        self.assertEqual(
            len(r),
            0
        )

    def test_get_message(self):
        msg = Message.objects.get(pk=1)
        response = self.client.get(
            reverse('messages', kwargs={'pk': msg.pk}),
        )
        r = json.loads(response.content)
        self.assertEqual(
            r['subject'],
            msg.subject
        )

    def test_get_unauthorized_message(self):
        """Ensure that other people's messages aren't retrievable"""
        msg = Message.objects.get(pk=5)
        response = self.client.get(
            reverse('messages', kwargs={'pk': msg.pk}),
        )
        self.assertEqual(
            response.status_code,
            403
        )

    def test_convert_to_node(self):
        message = Message.objects.get(pk=1)
        node = message.source_node
        self.assertTrue(
            node.todo_state.abbreviation,
            'DFRD'
        )
        url = reverse('messages', kwargs={'pk': message.pk})
        response = self.client.put(
            url,
            json.dumps({'action': 'create_node',
                        'title': 'man of action',
                        'parent': 1}),
            content_type='application/json'
        )
        r = json.loads(response.content)
        self.assertEqual(
            r['status'],
            'success',
        )
        self.assertEqual(
            r['result'],
            'message_deleted'
        )
        self.assertEqual(
            Message.objects.filter(pk=1).count(),
            0,
            'Deferred message is not deleted after node is created'
        )
        node = Node.objects.get(pk=node.pk)
        self.assertEqual(
            node.todo_state.abbreviation,
            'NEXT',
            'create_node action does not set new nodes todo_state'
        )
        self.assertEqual(
            node.title,
            'man of action',
            'Title not set on new node'
        )
        self.assertEqual(
            node.parent,
            Node.objects.get(pk=1),
            'Parent not set'
        )

    def test_convert_to_closed_node(self):
        message = Message.objects.get(pk=1)
        node = message.source_node
        url = reverse('messages', kwargs={'pk': message.pk})
        self.client.put(
            url,
            json.dumps({'action': 'create_node',
                        'close': True}),
            content_type='application/json'
        )
        node = Node.objects.get(pk=node.pk)
        self.assertEqual(
            node.todo_state.abbreviation,
            'DONE'
        )

    def test_convert_repeating_to_node(self):
        message = Message.objects.get(pk=2)
        url = reverse('messages', kwargs={'pk': message.pk})
        self.client.put(
            url,
            json.dumps({'action': 'create_node'}),
            content_type='application/json'
        )
        self.assertEqual(
            Message.objects.filter(pk=message.pk).count(),
            1,
            'Deferred message deleted after repeating node is created'
        )

    def test_filter_inbox_by_date(self):
        """
        Make sure that the view handles string dates appropriately.
        Specifically, it needs to convert from UTC to current timezone.
        """
        curr_dt = dt.datetime(2014, 1, 5,
                              4, 0, 0,
                              tzinfo=pytz.utc)
        tz_str = curr_dt.astimezone(get_current_timezone()).isoformat()
        qs = Message.objects.filter(owner=self.user, rcvd_date__lte=curr_dt)
        response = self.client.get(self.url, {'rcvd_date__lte': tz_str})
        r = json.loads(response.content)
        self.assertQuerysetEqual(
            qs,
            [x['subject'] for x in r],
            transform=lambda x: x.subject,
            ordered=False
        )

    def test_post_new_message(self):
        data = {
            'subject': 'find a place for dinner',
            'handler_path': 'plugins.quickcapture',
        }
        response = self.client.post(
            self.url, data
        )
        r = json.loads(response.content)
        msg = Message.objects.get(pk=r['id'])
        self.assertEqual(
            msg.subject,
            data['subject'],
        )

    def test_delete_message(self):
        """
        Delete a message via the API
        """
        msg = Message.objects.get(pk=4)
        url = reverse('messages', kwargs={'pk': msg.pk})
        response = self.client.delete(url)
        r = json.loads(response.content)
        self.assertEqual(
            Message.objects.filter(pk=4).count(),
            0,
            'Message not deleted'
        )
        self.assertEqual(
            r['status'],
            'success',
        )
        self.assertEqual(
            r['result'],
            'message_deleted'
        )

    def test_delete_message_bad_url(self):
        """
        Delete a message via the API
        """
        url = reverse('messages')
        response = self.client.delete(url)
        self.assertEqual(
            response.status_code,
            405,
        )

    def test_archive(self):
        """
        Test that the 'archive' action functions properly.
        """
        msg = Message.objects.get(pk=1)
        url = reverse('messages', kwargs={'pk': msg.pk})
        self.assertTrue(
            msg.in_inbox,
            'Message starts out with in_inbox=False (bad fixture?)'
        )
        self.client.put(url,
                        json.dumps({'action': 'archive'}),
                        content_type='application/json')
        msg = Message.objects.get(pk=1)
        self.assertTrue(
            not msg.in_inbox,
            'Message not changed'
        )

    def test_defer(self):
        """
        Test that the 'defer' action functions properly.
        """
        msg = Message.objects.get(pk=1)
        url = reverse('messages', kwargs={'pk': msg.pk})
        now = dt.datetime(2014, 1, 2, tzinfo=get_current_timezone())
        msg.rcvd_date = now
        msg.save()
        # Send the API call to defer the Message()
        future_date = now + dt.timedelta(days=3)
        future_str = future_date.strftime('%Y-%m-%d')
        self.client.put(
            url,
            json.dumps({'action': 'defer',
                        'target_date': future_str}),
            content_type='application/json'
        )
        # Now check that the new rcvd_date is set
        msg = Message.objects.get(pk=1)
        self.assertEqual(
            msg.rcvd_date,
            future_date,
        )


class InboxSerializerTest(TestCase):
    """
    Check that the MessageSerializer works as expected for API calls
    """
    fixtures = ['test-users.json', 'messages-test.json',
                'gtd-env.json', 'gtd-test.json']

    def test_db_optimization(self):
        messages = Message.objects.all()
        serializer = InboxSerializer(messages, many=True)
        def eval_queryset():
            list(serializer.data)
        self.assertNumQueries(
            1,
            eval_queryset
        )

    def test_source_node(self):
        message = Message.objects.get(pk=1)
        node = message.source_node
        serializer = InboxSerializer(message)
        self.assertEqual(
            serializer.data['source_node'],
            node.pk
        )
        self.assertEqual(
            serializer.data['node_slug'],
            node.slug
        )

    def test_message_fields(self):
        messages = Message.objects.all()
        serializer = InboxSerializer(messages[0])
        included = ['id', 'subject', 'sender', 'unread',
                    'handler_path', 'rcvd_date',
                    'source_node', 'node_slug']
        self.assertEqual(
            included,
            serializer.data.keys(),
        )
