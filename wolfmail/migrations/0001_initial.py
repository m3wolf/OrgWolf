# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Message'
        db.create_table(u'wolfmail_message', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('subject', self.gf('django.db.models.fields.TextField')()),
            ('sender', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('recipient', self.gf('django.db.models.fields.TextField')(blank=True)),
            ('owner', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['orgwolf.OrgWolfUser'])),
            ('unread', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('handler_path', self.gf('django.db.models.fields.CharField')(max_length=100)),
            ('in_inbox', self.gf('django.db.models.fields.BooleanField')(default=True)),
            ('rcvd_date', self.gf('django.db.models.fields.DateTimeField')()),
            ('message_text', self.gf('django.db.models.fields.TextField')(blank=True)),
        ))
        db.send_create_signal(u'wolfmail', ['Message'])

        # Adding M2M table for field spawned_nodes on 'Message'
        db.create_table(u'wolfmail_message_spawned_nodes', (
            ('id', models.AutoField(verbose_name='ID', primary_key=True, auto_created=True)),
            ('message', models.ForeignKey(orm[u'wolfmail.message'], null=False)),
            ('node', models.ForeignKey(orm[u'gtd.node'], null=False))
        ))
        db.create_unique(u'wolfmail_message_spawned_nodes', ['message_id', 'node_id'])


    def backwards(self, orm):
        # Deleting model 'Message'
        db.delete_table(u'wolfmail_message')

        # Removing M2M table for field spawned_nodes on 'Message'
        db.delete_table('wolfmail_message_spawned_nodes')


    models = {
        u'auth.group': {
            'Meta': {'object_name': 'Group'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '80'}),
            'permissions': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['auth.Permission']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'auth.permission': {
            'Meta': {'ordering': "(u'content_type__app_label', u'content_type__model', u'codename')", 'unique_together': "((u'content_type', u'codename'),)", 'object_name': 'Permission'},
            'codename': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'content_type': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['contenttypes.ContentType']"}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'})
        },
        u'contenttypes.contenttype': {
            'Meta': {'ordering': "('name',)", 'unique_together': "(('app_label', 'model'),)", 'object_name': 'ContentType', 'db_table': "'django_content_type'"},
            'app_label': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'model': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '100'})
        },
        u'gtd.contact': {
            'Meta': {'object_name': 'Contact', '_ormbases': [u'gtd.Tag']},
            'f_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'l_name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'tag_ptr': ('django.db.models.fields.related.OneToOneField', [], {'to': u"orm['gtd.Tag']", 'unique': 'True', 'primary_key': 'True'}),
            'user': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['orgwolf.OrgWolfUser']", 'null': 'True', 'blank': 'True'})
        },
        u'gtd.node': {
            'Meta': {'object_name': 'Node'},
            'archived': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'assigned': ('django.db.models.fields.related.ForeignKey', [], {'blank': 'True', 'related_name': "u'assigned_node_set'", 'null': 'True', 'to': u"orm['gtd.Contact']"}),
            'closed': ('django.db.models.fields.DateTimeField', [], {'null': 'True', 'blank': 'True'}),
            'deadline_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'deadline_time': ('django.db.models.fields.TimeField', [], {'null': 'True', 'blank': 'True'}),
            'energy': ('django.db.models.fields.CharField', [], {'max_length': '2', 'null': 'True', 'blank': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            u'level': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            u'lft': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'opened': ('django.db.models.fields.DateTimeField', [], {'auto_now_add': 'True', 'null': 'True', 'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'related_name': "u'owned_node_set'", 'to': u"orm['orgwolf.OrgWolfUser']"}),
            'parent': ('mptt.fields.TreeForeignKey', [], {'blank': 'True', 'related_name': "u'children'", 'null': 'True', 'to': u"orm['gtd.Node']"}),
            'priority': ('django.db.models.fields.CharField', [], {'default': "u'B'", 'max_length': '1'}),
            'repeating_number': ('django.db.models.fields.IntegerField', [], {'null': 'True', 'blank': 'True'}),
            'repeating_unit': ('django.db.models.fields.CharField', [], {'max_length': '1', 'null': 'True', 'blank': 'True'}),
            'repeats': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'repeats_from_completion': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            u'rght': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'scheduled_date': ('django.db.models.fields.DateField', [], {'null': 'True', 'blank': 'True'}),
            'scheduled_time': ('django.db.models.fields.TimeField', [], {'null': 'True', 'blank': 'True'}),
            'scope': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['gtd.Scope']", 'symmetrical': 'False', 'blank': 'True'}),
            'slug': ('django.db.models.fields.SlugField', [], {'max_length': '50'}),
            'tag_string': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'time_needed': ('django.db.models.fields.CharField', [], {'max_length': '4', 'null': 'True', 'blank': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'todo_state': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['gtd.TodoState']", 'null': 'True', 'blank': 'True'}),
            u'tree_id': ('django.db.models.fields.PositiveIntegerField', [], {'db_index': 'True'}),
            'users': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['orgwolf.OrgWolfUser']", 'symmetrical': 'False', 'blank': 'True'})
        },
        u'gtd.scope': {
            'Meta': {'object_name': 'Scope'},
            'display': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'name': ('django.db.models.fields.CharField', [], {'max_length': '50'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['orgwolf.OrgWolfUser']", 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'False'})
        },
        u'gtd.tag': {
            'Meta': {'object_name': 'Tag'},
            'display': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['orgwolf.OrgWolfUser']", 'null': 'True', 'blank': 'True'}),
            'public': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'tag_string': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '10'})
        },
        u'gtd.todostate': {
            'Meta': {'ordering': "[u'order']", 'object_name': 'TodoState'},
            '_color_alpha': ('django.db.models.fields.FloatField', [], {'default': '0'}),
            '_color_rgb': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'abbreviation': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '10'}),
            'actionable': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'class_size': ('django.db.models.fields.IntegerField', [], {'default': '0'}),
            'closed': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'display_text': ('django.db.models.fields.CharField', [], {'max_length': '30'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'order': ('django.db.models.fields.IntegerField', [], {'default': '50'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['orgwolf.OrgWolfUser']", 'null': 'True', 'blank': 'True'})
        },
        u'orgwolf.orgwolfuser': {
            'Meta': {'object_name': 'OrgWolfUser'},
            'date_joined': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'email': ('django.db.models.fields.EmailField', [], {'max_length': '75', 'blank': 'True'}),
            'first_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'groups': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Group']"}),
            'home': ('django.db.models.fields.CharField', [], {'default': "'orgwolf.views.home'", 'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'is_active': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'is_staff': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'is_superuser': ('django.db.models.fields.BooleanField', [], {'default': 'False'}),
            'last_login': ('django.db.models.fields.DateTimeField', [], {'default': 'datetime.datetime.now'}),
            'last_name': ('django.db.models.fields.CharField', [], {'max_length': '30', 'blank': 'True'}),
            'password': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'preferred_timezone': ('django.db.models.fields.CharField', [], {'max_length': '25', 'blank': 'True'}),
            'user_permissions': ('django.db.models.fields.related.ManyToManyField', [], {'symmetrical': 'False', 'related_name': "u'user_set'", 'blank': 'True', 'to': u"orm['auth.Permission']"}),
            'username': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '30'})
        },
        u'wolfmail.message': {
            'Meta': {'object_name': 'Message'},
            'handler_path': ('django.db.models.fields.CharField', [], {'max_length': '100'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'in_inbox': ('django.db.models.fields.BooleanField', [], {'default': 'True'}),
            'message_text': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'owner': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['orgwolf.OrgWolfUser']"}),
            'rcvd_date': ('django.db.models.fields.DateTimeField', [], {}),
            'recipient': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'sender': ('django.db.models.fields.TextField', [], {'blank': 'True'}),
            'spawned_nodes': ('django.db.models.fields.related.ManyToManyField', [], {'to': u"orm['gtd.Node']", 'symmetrical': 'False', 'blank': 'True'}),
            'subject': ('django.db.models.fields.TextField', [], {}),
            'unread': ('django.db.models.fields.BooleanField', [], {'default': 'True'})
        }
    }

    complete_apps = ['wolfmail']