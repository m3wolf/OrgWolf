# -*- coding: utf-8 -*-
#######################################################################
# Copyright 2012 Mark Wolf
#
# This file is part of OrgWolf.
#
# OrgWolf is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#######################################################################

from __future__ import unicode_literals, absolute_import, print_function
import datetime
import json
import logging
import math
import re

from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.http import (HttpResponse, Http404,
                         HttpResponseBadRequest, HttpResponseNotAllowed)
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.utils.timezone import get_current_timezone
from django.views.generic import View
from django.views.generic.detail import DetailView
from rest_framework.views import APIView
from rest_framework.response import Response

from gtd.forms import NodeForm
from gtd.models import TodoState, Node, Context, Scope
from gtd.shortcuts import (parse_url, generate_url, get_todo_abbrevs,
                           order_nodes)
from gtd.serializers import (ContextSerializer, ScopeSerializer,
                             NodeSerializer, NodeListSerializer)
from orgwolf import settings

# Prepare logger
logger = logging.getLogger('gtd.views')

def home(request):
    pass # Todo GTD/home view

@login_required
def list_display(request, url_string=""):
    """Determines which list the user has requested and fetches it."""
    all_todo_states_query = TodoState.get_visible(request.user)
    all_scope_qs = Scope.objects.all()
    todo_states = all_todo_states_query
    list(todo_states)
    all_todo_states_json = TodoState.as_json(queryset = todo_states)
    todo_states_query = TodoState.objects.none()
    todo_abbrevs = get_todo_abbrevs(todo_states)
    todo_abbrevs_lc = []
    base_url = reverse('list_display')
    base_node_url = reverse('projects')
    list_url = base_url
    list_url += '{parent}{states}{scope}{context}'
    scope_url_data = {}
    tz = get_current_timezone()
    # scope_url = base_url # for urls of scope tabs
    if url_string == None:
        url_string = ""
    for todo_abbrev in todo_abbrevs:
        todo_abbrevs_lc.append(todo_abbrev.lower())
    # Handle requests to change the TODO, context and scope filters
    if request.method == "POST":
        todo_regex = re.compile(r'todo(\d+)')
        new_context_id = 0
        todo_state_Q = Q()
        empty_Q = True
        parent = None
        # Check for TODO filters
        for post_item in request.POST:
            todo_match = todo_regex.match(post_item)
            if todo_match:
                todo_state_Q = todo_state_Q | Q(id=todo_match.groups()[0])
                empty_Q = False
            elif post_item == 'context':
                new_context_id = int(request.POST['context'])
                # Update session variable if user is clearning the context
                if new_context_id == 0:
                    request.session['context'] = None
            elif post_item == 'scope':
                new_scope_id = int(request.POST['scope'])
            elif post_item == 'parent_id':
                parent = Node.objects.get(pk=request.POST['parent_id'])
        # Now build the new URL and redirect
        new_url = base_url
        if empty_Q:
            matched_todo_states = TodoState.objects.none()
        else:
            matched_todo_states = TodoState.objects.filter(todo_state_Q)
        if parent:
            new_url += 'parent{0}/'.format(parent.pk)
        for todo_state in matched_todo_states:
            new_url += todo_state.abbreviation.lower() + '/'
        if new_scope_id > 0:
            new_url += 'scope' + str(new_scope_id) + '/'
        if new_context_id > 0:
            new_url += 'context' + str(new_context_id) + '/'
        return redirect(new_url)
    # Get stored context value (or set if first visit)
    if 'context' not in request.session:
        request.session['context'] = None
    current_context = request.session['context']
    # Retrieve the context objects based on url
    url_data = parse_url(url_string, request, todo_states=todo_states)
    if url_data.get('context', False) != False: # `None` indicates context0
        if url_data.get('context') != current_context:
            # User is changing the context
            request.session['context'] = url_data.get('context')
            current_context = url_data.get('context')
    elif current_context:
        # Redirect to the url using the save context
        new_url = base_url + generate_url(
            parent=url_data.get('parent'),
            context=current_context
            )[1:] # Don't need leading '/'
        return redirect(new_url)
    # Filter by todo state (use of Q() objects means we only hit database once
    final_Q = Q()
    todo_states_query = url_data.get('todo_states', [])
    todo_string = ''
    for todo_state in todo_states_query:
        todo_string += '{0}/'.format(todo_state.abbreviation.lower())
        final_Q = final_Q | Q(todo_state=todo_state)
    scope_url_data['states'] = todo_string
    nodes = Node.objects.assigned(request.user).select_related(
        'context', 'todo_state', 'root'
    )
    nodes = nodes.filter(final_Q)
    root_nodes = Node.objects.mine(
        request.user, get_archived=True
    ).filter(level=0)
    # Now apply the context
    if current_context:
        scope_url_data['context'] = 'context{0}/'.format(
            current_context.pk
        )
    else:
        scope_url_data['context'] = ''
    try:
        nodes = current_context.apply(nodes)
    except AttributeError:
        pass
    # And filter by scope
    scope = url_data.get('scope', None)
    if scope:
        try:
            nodes = nodes.filter(scope=scope)
        except Node.ObjectDoesNotExist:
            pass
    # And filter by parent node
    parent = url_data.get('parent')
    if parent:
        nodes = nodes & parent.get_descendants(include_self=True)
        scope_url_data['parent'] = 'parent{0}/'.format(parent.pk)
        breadcrumb_list = parent.get_ancestors(include_self=True)
    else:
        scope_url_data['parent'] = ''
    # Put nodes with deadlines first
    nodes = order_nodes(nodes, field='deadline_date', context=current_context)
    # -------------------- Queryset evaluated -------------------- #
    # Prepare the URLs for use in the scope and parent links tabs
    scope_url = list_url.format(
        context = scope_url_data['context'],
        scope = '{scope}/',
        states = scope_url_data['states'],
        parent = scope_url_data['parent'],
    )
    if scope:
        scope_s = 'scope{0}/'.format(scope.pk)
    else:
        scope_s = ''
    parent_url = list_url.format(
        context = scope_url_data['context'],
        scope = scope_s,
        states = scope_url_data['states'],
        parent = 'parent{0}/'
    )
    # Add a field for the root node and deadline
    for node in nodes:
        # (uses lists in case of bad unit tests)
        root_node = [n for n in root_nodes if n.tree_id == node.tree_id]
        if len(root_node) > 0:
            node.root_url = parent_url.format(root_node[0].pk)
            node.root_title = root_node[0].title
        node.deadline_str = node.overdue('deadline_date')
    # And serve response
    return render_to_response('gtd/gtd_list.html',
                              locals(),
                              RequestContext(request))


def actions(request, context_id, context_slug):
    base_node_url = reverse('projects')
    template = 'gtd/node_list.html'
    return render_to_response(template,
                              locals(),
                              RequestContext(request))


class NodeListView(APIView):
    """
    Interacts with next-action style lists of <Node> objects
    """
    model = Node
    def dispatch(self, request, *args, **kwargs):
        """Set some properties first then call regular dispatch"""
        self.request = request
        self.todo_states = TodoState.get_visible(request.user)
        self.scope_url_data = {}
        list(self.todo_states)
        self.url_string = kwargs.get('url_string', '')
        if self.url_string is None:
            self.url_string = ''
        self.url_data = parse_url(self.url_string, request,
                                  todo_states=self.todo_states)
        self.base_url = reverse('list_display')
        return super(NodeListView, self).dispatch(request, *args, **kwargs)

    def get_queryset(self):
        parent_id = self.request.GET.get('parent', None)
        if parent_id is not None:
            parent = Node.objects.get(pk=parent_id)
            nodes = parent.get_descendants(include_self=True)
        else:
            nodes = Node.objects.all()
        nodes = nodes.assigned(self.request.user).select_related(
            'context', 'todo_state', 'root'
        )
        # Filter by todo state
        final_Q = Q()
        todo_states_query = self.url_data.get('todo_state', [])
        todo_string = ''
        for todo_state in todo_states_query:
            todo_string += '{0}/'.format(todo_state.abbreviation.lower())
            final_Q = final_Q | Q(todo_state=todo_state)
        self.scope_url_data['states'] = todo_string
        nodes = nodes.filter(final_Q)
        # And filter by scope
        self.scope = self.url_data.get('scope', None)
        if self.scope:
            try:
                nodes = nodes.filter(scope=self.scope)
            except Node.ObjectDoesNotExist:
                pass
        # Filter by context
        self.context = self.url_data.get('context', None)
        if self.context is not None:
            nodes = self.context.apply(nodes)
        return nodes

    def post(self, request, *args, **kwargs):
        """Change active filtering parameters"""
        base_url = self.base_url
        todo_regex = re.compile(r'todo(\d+)')
        new_context_id = 0
        todo_state_Q = Q()
        empty_Q = True
        parent = None
        # Check for TODO filters
        for post_item in request.POST:
            todo_match = todo_regex.match(post_item)
            if todo_match:
                todo_state_Q = todo_state_Q | Q(id=todo_match.groups()[0])
                empty_Q = False
            elif post_item == 'context':
                new_context_id = int(request.POST['context'])
                # Update session variable if user is clearning the context
                if new_context_id == 0:
                    request.session['context'] = None
            elif post_item == 'scope':
                new_scope_id = int(request.POST['scope'])
            elif post_item == 'parent_id':
                parent = Node.objects.get(pk=request.POST['parent_id'])
        # Now build the new URL and redirect
        new_url = base_url
        if empty_Q:
            matched_todo_states = TodoState.objects.none()
        else:
            matched_todo_states = TodoState.objects.filter(todo_state_Q)
        if parent:
            new_url += 'parent{0}/'.format(parent.pk)
        for todo_state in matched_todo_states:
            new_url += todo_state.abbreviation.lower() + '/'
        if new_scope_id > 0:
            new_url += 'scope' + str(new_scope_id) + '/'
        if new_context_id > 0:
            new_url += 'context' + str(new_context_id) + '/'
        return redirect(new_url)

    def get(self, request, *args, **kwargs):
        """Determines which list the user has requested and fetches it."""
        # Get objects based on url parameters
        todo_states = request.GET.getlist('todo_state', [''])
        if todo_states != ['']:
            self.url_data['todo_state'] = self.todo_states.filter(
                pk__in=todo_states
            )
            # Check that all todo_states requested are valid
            if len(self.url_data['todo_state']) != len(todo_states):
                return HttpResponseBadRequest('Invalid todo_state passed')
        scope = request.GET.get('scope', '')
        if scope:
            self.url_data['scope'] = Scope.objects.get(pk=scope)
        context = request.GET.get('context', '')
        if context:
            # self.url_data['context'] = Context.objects.get(pk=context)
            self.url_data['context'] = get_object_or_404(Context, pk=context)
        # Update the current context
        new_context_id = request.GET.get('context', None)
        if new_context_id is not None:
            new_context = Context.objects.get(pk=new_context_id)
            request.session['context_name'] = new_context.name
        request.session['context_id'] = new_context_id
        nodes = self.get_queryset()
        serializer = NodeListSerializer(nodes, many=True)
        return Response(serializer.data)


class NodeView(APIView):
    """
    API for interacting with Node objects. Unauthenticated requests
    are permitted but do not alter the database.
    """
    def get(self, request, *args, **kwargs):
        """Returns the details of the node as a json encoded object"""
        BOOLS = ('archived',) # Translate 'False' -> False for these fields
        get_dict = request.QUERY_PARAMS.copy()
        node_id = kwargs.get('pk')
        parent_id = get_dict.get('parent_id', None)
        if parent_id == '0':
            get_dict['parent_id'] = None
        if node_id is None:
            # All nodes
            nodes = Node.objects.mine(request.user, get_archived=True)
            # Apply each criterion to the queryset
            for param, value in get_dict.iteritems():
                if param in BOOLS and value == 'false':
                    value = False
                query = {param: value}
                nodes = nodes.filter(**query)
            serializer = NodeSerializer(nodes, many=True)
        else:
            node = get_object_or_404(Node, pk=node_id)
            serializer = NodeSerializer(node)
        return Response(serializer.data)

    def post(self, request, pk=None, *args, **kwargs):
        """
        Create a new Node, conducted through JSON format:
        {
          id: [node primary key],
          field: (eg. title),
          field: (eg. todo_state),
          etc...
        }

        Ignores fields related to MPTT for new nodes as these get
        set automatically based on the 'parent' attribute.

        Returns: JSON object of all node fields, with changes.
        """
        data = request.DATA.copy()
        if pk is not None:
            return HttpResponseNotAllowed(['GET', 'PUT'])
        # Create new node
        self.node = Node()
        if not request.user.is_anonymous():
            self.node.owner = request.user
        self.node.save()
        # Set fields (ignore mptt fields for new nodes)
        for key in ('id', 'tree_id', 'lft', 'rght', 'level'):
            try:
                data.pop(key)
            except KeyError:
                pass
        self.node.set_fields(data)
        self.node.save()
        # Return newly saved node as json
        self.node = Node.objects.get(pk=self.node.pk)
        serializer = NodeSerializer(self.node)
        data = serializer.data
        # Don't keep nodes sent via the public interface
        if request.user.is_anonymous():
            self.node.delete()
        return Response(data)

    def put(self, request, pk=None, *args, **kwargs):
        """
        Edit existing nodes through JSON format:
        {
          id: [node primary key],
          field: (eg. title),
          field: (eg. todo_state),
          etc...
        }
        """
        if pk is None:
            # Throw error response if user is trying to
            # PUT without specifying a pk
            return HttpResponseNotAllowed(['GET', 'POST'])
        data = request.DATA.copy()
        # Remove tree metadata from the request
        TREE_FIELDS = ('lft', 'rght', 'level', 'tree_id')
        for key in TREE_FIELDS:
            try:
                data.pop(key)
            except KeyError:
                pass
        # Check the permissions of the Node
        node = get_object_or_404(Node, pk=pk)
        access = node.access_level(request.user)
        if ((request.user.is_anonymous() and node.owner is not None) or
            (not request.user.is_anonymous() and access != 'write')):
            # Not authorized
            return HttpResponse(
                json.dumps({'status': 'failure',
                            'reason': 'unauthorized'}),
                status=401)
        # Update and return the Node
        node.set_fields(data)
        if not request.user.is_anonymous():
            node.save()
            node = Node.objects.get(pk=node.pk)
        serializer = NodeSerializer(node)
        return Response(serializer.data)


class UpcomingNodeView(APIView):
    """
    Returns a list of nodes that have upcoming deadlines, based on the
    optional date passed: /gtd/node/upcoming[/year/month/day/]
    """
    def get(self, request, year=None, month=None, day=None):
        deadline_period = 7 # in days
        all_nodes_qs = Node.objects.mine(request.user)
        if year is None:
            # Default to today
            target_date = datetime.date.today()
        # Determine query filters for "Upcoming Deadlines" section
        undone_Q = Q(todo_state__closed = False) | Q(todo_state = None)
        deadline = target_date + datetime.timedelta(days=deadline_period)
        upcoming_deadline_Q = Q(deadline_date__lte = deadline) # TODO: fix this
        deadline_nodes = all_nodes_qs.filter(undone_Q, upcoming_deadline_Q)
        deadline_nodes = deadline_nodes.order_by("deadline_date")
        serializer = NodeListSerializer(deadline_nodes, many=True)
        return Response(serializer.data)


class ProjectView(DetailView):
    """Manages the retrieval of a tree view for the nodes"""
    model = Node
    template_name = 'gtd/node_view.html'
    context_object_name = 'parent_node'
    # @method_decorator(login_required)
    # def dispatch(self, *args, **kwargs):
    #     return super(ProjectView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        # First unpack arguments
        node_id = kwargs.get('pk')
        scope_id = 0
        show_all = request.GET.get('archived')
        slug = kwargs.get('slug')
        # Some setup work
        all_nodes_qs = Node.objects.mine(request.user, get_archived=show_all)
        all_todo_states_qs = TodoState.get_visible(user=request.user)
        child_nodes_qs = all_nodes_qs
        app_url = reverse('projects')
        scope_url = app_url + '{scope}/'
        scope = Scope.objects.get(pk=1)
        url_data = {}
        url_kwargs = {}
        # If the user asked for a specific node
        if node_id:
            scope_url += '{0}/'.format(node_id)
            child_nodes_qs = child_nodes_qs.filter(parent__id=node_id)
            parent_node = Node.objects.get(id=node_id)
            parent_json = serializers.serialize('json', [parent_node])
            parent_tags = parent_node.get_tags()
            breadcrumb_list = parent_node.get_ancestors(include_self=True)
            # Redirect in case of incorrect slug
            if slug != parent_node.slug:
                return redirect(
                    reverse(
                        'projects',
                        kwargs={'pk': str(parent_node.pk),
                                'slug': parent_node.slug}
                    )
                )
        else:
            child_nodes_qs = child_nodes_qs.filter(parent=None)
        # Filter by scope
        if scope_id:
            scope = get_object_or_404(Scope, pk=scope_id)
            url_data['scope'] = scope
            child_nodes_qs = child_nodes_qs.filter(scope=scope)
            url_kwargs['scope_id'] = scope_id
        base_url = reverse('projects', kwargs=url_kwargs)
        if node_id:
            url_kwargs['pk'] = parent_node.pk
            url_kwargs['slug'] = parent_node.slug
        node_url = reverse('projects', kwargs=url_kwargs)
        # Make sure user is authorized to see this node
        if node_id:
            if not (parent_node.access_level(request.user) in ['write', 'read']):
                new_url = reverse('django.contrib.auth.views.login')
                new_url += '?next=' + base_url + '/' + node_id + '/'
                return redirect(new_url)
        if node_id == None:
            node_id = 0
        all_todo_states_json = TodoState.as_json(all_todo_states_qs,
                                                 user=request.user)
        all_todo_states_json_full = TodoState.as_json(
            queryset=all_todo_states_qs,
            full=True,
            user=request.user
            )
        return render_to_response('gtd/node_view.html',
                                  locals(),
                                  RequestContext(request))

    def post(self, request, *args, **kwargs):
        post = request.POST
        url_kwargs = {}
        new = "No"
        node_id = kwargs['pk']
        try:
            self.node = Node.objects.mine(request.user,
                                  get_archived=True).get(pk=node_id)
        except Node.DoesNotExist:
            # If the node is not accessible return a 404
            raise Http404()
        scope_id = kwargs.get('scope_id')
        if scope_id:
            url_kwargs['scope_id'] = scope_id
        url_kwargs['slug'] = self.node.slug
        base_url = reverse('projects', kwargs=url_kwargs) + '/'
        breadcrumb_list = self.node.get_ancestors(include_self=True)
        # Make sure user is authorized to edit this node
        if self.node.access_level(request.user) != 'write':
            new_url = reverse('django.contrib.auth.views.login')
            new_url += '?next=' + base_url + node_id + '/'
            return redirect(new_url)
        if (request.method == "POST" and
              request.POST.get('function') == 'reorder'):
            # User is trying to move the node up or down
            if 'move_up' in request.POST:
                self.node.move_to(self.node.get_previous_sibling(),
                             position='left'
                             )
            elif 'move_down' in request.POST:
                self.node.move_to(self.node.get_next_sibling(),
                             position='right'
                             )
            else:
                return HttpResponseBadRequest('Missing request data')
            if self.node.parent:
                url_kwargs['pk'] = self.node.parent.pk
            redirect_url = reverse('projects', kwargs=url_kwargs)
            return redirect(redirect_url)
        elif (request.method == 'POST' and
              request.POST.get('function') == 'change_todo_state'):
            # User has asked to change TodoState
            new_todo_id = request.POST['new_todo']
            if new_todo_id == '0':
                self.node.todo_state = None
            else:
                self.node.todo_state = TodoState.objects.get(pk=new_todo_id)
            self.node.auto_update = True
            self.node.save()
            todo_state = self.node.todo_state
            url_kwargs['pk'] = self.node.pk
            redirect_url = reverse('projects', kwargs=url_kwargs)
            return redirect(redirect_url)
        elif request.method == "POST": # Form submission
            post = request.POST
            form = NodeForm(request.POST, instance=self.node)
            if form.is_valid():
                form.save()
                url_kwargs['pk'] = node_id
                redirect_url = reverse('projects', kwargs=url_kwargs)
                return redirect(redirect_url)
        else: # Blank form
            form = NodeForm(instance=self.node)
        return render_to_response('gtd/node_edit.html',
                                  locals(),
                                  RequestContext(request))


class TodoStateView(View):
    """Handles RESTful retrieval of TodoState objects"""
    def get(self, request, *args, **kwargs):
        todo_states = TodoState.get_visible(user=request.user)
        if request.is_ajax() or not settings.DEBUG_BAR:
            return HttpResponse(
                serializers.serialize('json', todo_states)
            )
        else:
            serializers.serialize('json', todo_states)
            # Non-ajax returns the base template to show django-debug-toolbar
            return render_to_response('base.html',
                                      locals(),
                                      RequestContext(request))


class ScopeView(APIView):
    """RESTful interaction with the gtd.Scope object"""
    def get(self, request, *args, **kwargs):
        scopes = Scope.get_visible(request.user)
        serializer = ScopeSerializer(scopes, many=True)
        return Response(serializer.data)


class ContextView(APIView):
    """RESTful interaction with the gtd.context object"""
    def get(self, request, *args, **kwargs):
        contexts = Context.get_visible(request.user)
        serializer = ContextSerializer(contexts, many=True)
        return Response(serializer.data)


@login_required
def get_descendants(request, ancestor_pk):
    """Looks up the descendants of the given parent. Optionally
    filtered by offset (eg offset of 1 is children (default), 2 is
    grandchildren, etc."""
    offset = request.GET.get('offset', 1)
    if int(ancestor_pk) > 0:
        parent = get_object_or_404(Node, pk=ancestor_pk)
        all_descendants = parent.get_descendants()
        level = parent.level + int(offset)
    elif int(ancestor_pk) == 0:
        parent = None
        all_descendants = Node.objects.all()
        level = int(offset)-1
    nodes_qs = all_descendants.filter(level=level)
    nodes_qs = nodes_qs & Node.objects.mine(request.user, get_archived=True)
    if request.is_ajax() or not settings.DEBUG_BAR:
        return HttpResponse(json.dumps(data))
    else:
        return render_to_response('base.html',
                                  locals(),
                                  RequestContext(request))


@login_required
def node_search(request):
    """Simple search module."""
    if request.GET.has_key('q'):
        query = request.GET['q']
        page = int(request.GET.get('page', 1))
        count = int(request.GET.get('count', 50))
        root_nodes = Node.objects.mine(
            request.user, get_archived=True
        ).filter(level=0)
        results = Node.search(
            query,
            request.user,
            page-1,
            count,
        )
        nodes_found = results[0]
        num_found = len(results[0])
        total_found = results[1]
        num_pages = int(math.ceil(total_found/float(count)))
        found_range = '{0}-{1}'.format(
            (page-1)*count + 1,
            (page-1)*count + num_found
        )
        # Figure out pagination details
        search_url = '{0}?q={1}&page={2}&count={3}'.format(
            reverse('gtd.views.node_search'),
            query,
            '{0}',
            count,
        )
        if num_pages > 1:
            pages = []
            if page != 1:
                prev = {'url': search_url.format(page-1),
                        'display': 'Prev',
                        'icon': 'arrow-l'}
                pages.append(prev)
            for x in range(num_pages):
                page_num = x+1
                new_page = {
                    'url': search_url.format(page_num),
                    'display': page_num
                }
                if page_num == page:
                    new_page['class'] = 'active'
                    del new_page['url']
                pages.append(new_page)
            if page != num_pages:
                nextt = {'url': search_url.format(page+1),
                         'display': 'Next',
                         'icon': 'arrow-r',
                         'iconpos': 'right'}
                pages.append(nextt)
        # Add a field for the root node
        for node in nodes_found:
            # (uses lists in case of bad unit tests)
            root_node = [n for n in root_nodes if n.tree_id == node.tree_id]
            if len(root_node) > 0:
                node.root_title = root_node[0].title
    else:
        query = ''
    base_url = reverse('projects')
    return render_to_response('gtd/node_search.html',
                              locals(),
                              RequestContext(request))
