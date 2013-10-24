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
from itertools import chain

from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.core.urlresolvers import reverse
from django.db.models import Q
from django.forms.models import model_to_dict
from django.http import (
    HttpResponse, HttpResponseRedirect, Http404, HttpResponseBadRequest)
from django.shortcuts import render_to_response, redirect, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.utils.decorators import method_decorator
from django.utils.timezone import get_current_timezone
from django.views.generic import View
from django.views.generic.detail import DetailView

from gtd.forms import NodeForm
from gtd.models import TodoState, Node, Context, Scope
from gtd.shortcuts import (parse_url, generate_url, get_todo_abbrevs,
                           order_nodes)
from gtd.templatetags.gtd_extras import escape_html
from mptt.exceptions import InvalidMove
from orgwolf import settings
from orgwolf.models import OrgWolfUser as User
from wolfmail.models import MailItem, Label

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
    base_url = reverse('gtd.views.list_display')
    base_node_url = reverse('node_object')
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
    nodes = order_nodes(nodes, field='deadline', context=current_context)
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
        node.deadline_str = node.overdue('deadline', tzinfo=tz)
    # And serve response
    if request.is_mobile:
        template = 'gtd/gtd_list_m.html'
    else:
        template = 'gtd/gtd_list.html'
    return render_to_response(template,
                              locals(),
                              RequestContext(request))

@login_required
def agenda_display(request, date=None):
    logger.debug('agenda_display() view called')
    format_string = "%Y-%m-%d"
    if request.method == "POST":
        # Check and process the new date
        try:
            datetime.datetime.strptime(request.POST['date'], format_string)
        except ValueError:
            pass
        else:
            new_url = "/gtd/agenda/" + request.POST['date']
            return redirect(new_url)
    deadline_period = 7 # In days # TODO: pull deadline period from user
    all_nodes_qs = Node.objects.mine(request.user).select_related('todo_state')
    tz = get_current_timezone()
    final_Q = Q()
    if date:
        try:
            agenda_date = datetime.datetime.strptime(date, format_string).date()
        except ValueError:
            raise Http404
    else:
        agenda_date = datetime.date.today()
    agenda_dt = datetime.datetime(
        year=agenda_date.year,
        month=agenda_date.month,
        day=agenda_date.day,
        hour=23, minute=59,
        second=59,
        tzinfo=tz
    ).astimezone(tz)
    logger.debug(
        'agenda_date = {0} | agenda_dt = {1}'.format(
            agenda_date,
            agenda_dt,
        )
    )
    agenda_dt_str = agenda_dt.strftime('%Y-%m-%d')
    one_day = datetime.timedelta(days=1)
    tomorrow = agenda_date + one_day
    yesterday = agenda_date - one_day
    # Determine query filters for "Today" section
    date_Q = Q(scheduled__lte=agenda_dt)
    time_specific_Q = Q(scheduled_time_specific=False)
    # TODO: allow user to set todo states
    todo_states = TodoState.get_visible(request.user)
    hard_Q = Q(todo_state = todo_states.get(abbreviation="HARD"))
    dfrd_Q = Q(todo_state = todo_states.get(abbreviation="DFRD"))
    day_specific_nodes = all_nodes_qs.filter(
        (hard_Q | dfrd_Q), date_Q, time_specific_Q)
    day_specific_nodes = day_specific_nodes.order_by('scheduled')
    time_specific_Q = Q(scheduled_time_specific=True)
    time_specific_nodes = all_nodes_qs.filter(
        (hard_Q | dfrd_Q), date_Q, time_specific_Q)
    time_specific_nodes = time_specific_nodes.order_by('scheduled')
    # Determine query filters for "Upcoming Deadlines" section
    undone_Q = Q(todo_state__closed = False) | Q(todo_state = None)
    deadline = agenda_dt + datetime.timedelta(days=deadline_period)
    upcoming_deadline_Q = Q(deadline__lte = deadline) # TODO: fix this
    deadline_nodes = all_nodes_qs.filter(undone_Q, upcoming_deadline_Q)
    deadline_nodes = deadline_nodes.order_by("deadline")
    # Force database hits and then add overdue data
    day_specific_nodes = list(day_specific_nodes)
    time_specific_nodes = list(time_specific_nodes)
    deadline_nodes = list(deadline_nodes)
    for node in day_specific_nodes:
        node.overdue_str = node.overdue(
            'scheduled', tzinfo=tz, agenda_dt=agenda_dt)
    for node in time_specific_nodes:
        node.overdue_str = node.overdue(
            'scheduled', tzinfo=tz, agenda_dt=agenda_dt)
    for node in deadline_nodes:
        node.overdue_str = node.overdue(
            'deadline', tzinfo=tz, agenda_dt=agenda_dt, future=True)
    # Create some data for javascript plugins
    all_todo_states_json = TodoState.as_json(queryset=todo_states,
                                             user=request.user)
    if request.GET.get('format') == 'json':
        # Render just the table rows for AJAX functionality
        json_data = {'status': 'success'}
        json_data['daily_html'] = render_to_string(
            'gtd/agenda_daily.html',
            locals(),
            RequestContext(request))
        json_data['timely_html'] = render_to_string(
            'gtd/agenda_timely.html',
            locals(),
            RequestContext(request))
        json_data['deadlines_html'] = render_to_string(
            'gtd/agenda_deadlines.html',
            locals(),
            RequestContext(request))
        return HttpResponse(json.dumps(json_data))
    if request.is_mobile:
        template = 'gtd/agenda_m.html'
    else:
        template = 'gtd/agenda.html'
    return render_to_response(template,
                              locals(),
                              RequestContext(request))

@login_required
def capture_to_inbox(request):
    """Processes the "capture widget" that appears on each page.
    Basically, this view adds the item as a MailTime with the Inbox label."""
    previous_url = request.GET.get('next', '/')
    if request.method == 'POST':
        if request.POST['new_inbox_item'] != "":
            new_item = MailItem()
            new_item.sender = "Captured"
            new_item.recipient
            new_item.owner = request.user
            new_item.subject = request.POST['new_inbox_item']
            new_item.rcvd_date = datetime.datetime.now()
            new_item.full_clean()
            new_item.save()
            new_item.labels.add(Label.objects.get(name="Inbox"))
    # TODO: automatically redirect using django.messaging
    return render_to_response('gtd/capture_success.html',
                              locals(),
                              RequestContext(request))

@login_required
def display_node(request, show_all=False, node_id=None, scope_id=None):
    """Displays a node as a list of links to its children.
    If no node_id is specified, shows the projects list."""
    if request.method == "POST":
        if request.POST['function'] == 'filter':
            # User has asked to filter
            url_kwargs = {}
            if int(request.POST['scope']) > 0:
                url_kwargs['scope_id'] = request.POST['scope']
            if request.POST['node_id']:
                url_kwargs['node_id'] = request.POST['node_id']
            return redirect(reverse('node_object', kwargs=url_kwargs))

@login_required
def edit_node(request, node_id, scope_id, slug):
    """Display a form to allow the user to edit a node"""
    if request.method == 'POST':
        post = request.POST
    url_kwargs = {}
    new = "No"
    node = Node.objects.get(pk=node_id)
    if scope_id:
        url_kwargs['scope_id'] = scope_id
    url_kwargs['slug'] = node.slug
    base_url = reverse('node_object', kwargs=url_kwargs)
    breadcrumb_list = node.get_ancestors(include_self=True)
    # Make sure user is authorized to edit this node
    if node.access_level(request.user) != 'write':
        new_url = reverse('django.contrib.auth.views.login')
        new_url += '?next=' + base_url + node_id + '/'
        return redirect(new_url)
    if request.is_ajax() and request.POST.get('format') == 'json':
        # Handle JSON requests
        post = request.POST
        try:
            node = Node.objects.owned(request.user,
                                  get_archived=True).get(pk=node_id)
        except Node.DoesNotExist:
            # If the node is not accessible return a 404
            return HttpResponse(json.dumps({'status': '404'}))
        if post.get('form') == 'modal':
            # Form posted from the modal javascript dialog
            if post.get('todo_state') == '0':
                post.pop('todo_state')
            form = NodeForm(post, instance=node)
            if form.is_valid():
                if post.get('auto_update') == 'false':
                    form.auto_update = False
                form.save()
                node = Node.objects.get(pk=node.pk)
                # Prepare the response
                node_data = node.as_pre_json()
                data = {
                    'status': 'success',
                    'node_id': node.pk,
                    'node_data': node_data,
                    }
            else:
                print(form.errors)
                return HttpResponseBadRequest(form.errors)
        else: # if post.get('form') != 'modal':
            # Text
            new_text = post.get('text', node.text)
            if new_text == '\n<br>':
                new_text = ''
            node.text = new_text
            # todo_state
            new_todo_id = post.get('todo_id', None)
            if new_todo_id == '0':
                node.todo_state = None
            elif new_todo_id > 0:
                try:
                    node.todo_state = TodoState.objects.get(pk=new_todo_id)
                except TodoState.DoesNotExist:
                    return HttpResponseBadRequest(
                        'Invalid todo_id: %s' % new_todo_id)
            # auto_repeat
            if post.get('auto_update') == 'false':
                node.auto_update = False
            else:
                node.auto_update = True
            # archived
            archived = post.get('archived')
            if archived == 'true':
                node.archived = True
            elif archived == 'false':
                node.archived = False
            node.save()
            data = {
                'status': 'success',
                'node_id': node.pk,
                'todo_id': getattr(node.todo_state, 'pk', 0),
                'text': node.text,
                'archived': node.archived,
                }
        return HttpResponse(json.dumps(data))
    if request.is_ajax() and request.GET.get('format') == 'modal_form':
        # User asked for the modal form used in jQuery plugins
        form = NodeForm(instance=node)
        return render_to_response('gtd/node_edit_modal.html',
                                  locals(),
                                  RequestContext(request))
    elif request.method == "POST" and request.POST.get('function') == 'reorder':
        # User is trying to move the node up or down
        if 'move_up' in request.POST:
            node.move_to(node.get_previous_sibling(),
                         position='left'
                         )
        elif 'move_down' in request.POST:
            node.move_to(node.get_next_sibling(),
                         position='right'
                         )
        else:
            return HttpResponseBadRequest('Missing request data')
        if node.parent:
            url_kwargs['pk'] = node.parent.pk
        redirect_url = reverse('node_object', kwargs=url_kwargs)
        return redirect(redirect_url)
    elif (request.method == 'POST' and
          request.POST.get('function') == 'change_todo_state'):
        # User has asked to change TodoState
        new_todo_id = request.POST['new_todo']
        if new_todo_id == '0':
            node.todo_state = None
        else:
            node.todo_state = TodoState.objects.get(pk=new_todo_id)
        node.auto_update = True
        node.save()
        todo_state = node.todo_state
        url_kwargs['pk'] = node.pk
        redirect_url = reverse('node_object', kwargs=url_kwargs)
        return redirect(redirect_url)
    elif request.method == "POST": # Form submission
        post = request.POST
        form = NodeForm(request.POST, instance=node)
        if form.is_valid():
            form.save()
            url_kwargs['pk'] = node_id
            redirect_url = reverse('node_object', kwargs=url_kwargs)
            return redirect(redirect_url)
    else: # Blank form
        form = NodeForm(instance=node, user=request.user)
    if request.is_mobile:
        template = 'gtd/node_edit_m.html'
    else:
        template = 'gtd/node_edit.html'
    return render_to_response(template,
                              locals(),
                              RequestContext(request))

@login_required
def move_node(request, node_id, scope_id):
    """Allows a user to change the location of a Node within it's tree or
    switch trees altogether."""
    post = request.POST
    url_kwargs = {}
    if scope_id:
        url_kwargs['scope_id'] = scope_id
    node = Node.objects.get(pk=node_id)
    if request.method == 'POST' and request.POST.get('function') == 'move':
        # User is trying to change the parent of the Node instance
        target_id = post.get('target_id')
        if target_id == 'None' or target_id == None:
            target = None
        else:
            try:
                target = Node.objects.get(pk=post.get('target_id'))
            except Node.DoesNotExist:

                return HttpResponseBadRequest(
                    'Please post a valid value for \'target_id\'. '.join(
                        'Received \'{0}\''.format(target_id) ))
        node.parent = target
        try:
            node.save()
        except InvalidMove:
            return HttpResponseBadRequest(
                'A node may not be made a child of any of its descendents')
        url_kwargs['pk'] = node.pk
        redir_url = reverse('node_object', kwargs=url_kwargs)
        return redirect(redir_url)
    # No action, so prompt the user for the new parent
    list = [] # Hold the final output
    # Prepare the current tree
    tree = node.get_root().get_descendants(include_self=True)
    for child in tree:
        if not child.is_descendant_of(node):
            indent = ''
            for i in range(0, child.level):
                indent += '---'
            if child == node:
                is_active = False
            else:
                is_active = True
            list.append({'instance': child,
                         'indent': indent,
                         'is_active': is_active,
                         })
    # Prepare the other root nodes
    others = Node.objects.filter(level=0).exclude(tree_id=node.tree_id)
    for other in others:
        list.append({'instance': other,
                     'is_active': True})
    template = 'gtd/node_move.html'
    return render_to_response(template,
                              locals(),
                              RequestContext(request))

@login_required
def new_node(request, node_id, scope_id):
    """Display a form to allow the user to create a new node"""
    url_kwargs = {}
    if scope_id:
        url_kwargs['scope_id'] = scope_id
    base_url = reverse('node_object', kwargs=url_kwargs)
    new = "Yes" # Used in template logic
    node = None
    if node_id:
        node = Node.objects.get(pk=node_id)
        breadcrumb_list = node.get_ancestors(include_self=True)
    if request.is_ajax() and request.GET.get('format') == 'modal_form':
        # User asked for the modal form used in jQuery plugins
        form = NodeForm(parent=node)
        return render_to_response('gtd/node_edit_modal.html',
                                  locals(),
                                  RequestContext(request))
    if request.is_ajax() and request.POST.get('format') == 'json':
        # Handle json requests
        post = request.POST;
        if post.get('form') == 'modal':
            # Form posted from the modal javascript dialog
            if post.get('todo_state') == '0':
                post.pop('todo_state')
            form = NodeForm(post)
            if form.is_valid():
                # Create and save the object
                new_node = form.save(commit=False)
                new_node.owner = request.user
                new_node.parent = node
                new_node.save()
                form.save_m2m()
                data = serializers.serialize('json', [new_node])
            else:
                return HttpResponseBadRequest(str(form.errors))
        return HttpResponse(json.dumps(data))
    if request.method == "POST": # Form submission
        form = NodeForm(request.POST, parent=node)
        if form.is_valid():
            form = form.save(commit=False)
            form.owner = request.user
            siblings = Node.objects.filter(parent__id=node_id)
            if node:
                form.parent = Node.objects.get(pk=node.pk)
            form.save()
            if request.POST.has_key('scope'):
                for new_scope_id in request.POST['scope']:
                    form.scope.add(Scope.objects.get(pk=new_scope_id))
            form.save()
            if hasattr(form.parent, 'pk'):
                url_kwargs['pk'] = form.parent.pk
            if 'add-another' in request.POST:
                redirect_url = reverse('gtd.views.new_node', kwargs=url_kwargs)
            else:
                redirect_url = reverse('node_object', kwargs=url_kwargs)
            return redirect(redirect_url)
    else: # Blank form
        initial_dict = {}
        projects = getattr(node, 'related_projects', None)
        form = NodeForm(parent=node)
    if request.is_mobile:
        template = 'gtd/node_edit_m.html'
    else:
        template = 'gtd/node_edit.html'
    return render_to_response(template,
                              locals(),
                              RequestContext(request))

class NodeView(DetailView):
    """Manages the retrieval of an individual node"""
    model = Node
    template_name = 'gtd/node_view.html'
    context_object_name = 'parent_node'
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(NodeView, self).dispatch(*args, **kwargs)

    def get(self, request, *args, **kwargs):
        if request.is_ajax() and not request.is_mobile:
            # AJAX request
            return self.get_json(request, *args, **kwargs)
        # First unpack arguments
        node_id = kwargs.get('pk')
        scope_id = 0
        show_all = request.GET.get('archived')
        slug = kwargs.get('slug')
        # Some setup work
        all_nodes_qs = Node.objects.mine(request.user, get_archived=show_all)
        all_todo_states_qs = TodoState.get_visible(user=request.user)
        child_nodes_qs = all_nodes_qs
        all_scope_qs = Scope.objects.all()
        all_scope_json = serializers.serialize('json', all_scope_qs)
        app_url = reverse('node_object')
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
                print(parent_node.slug + "*")
                return redirect(
                    reverse(
                        'node_object',
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
        base_url = reverse('node_object', kwargs=url_kwargs)
        if node_id:
            url_kwargs['pk'] = parent_node.pk
            url_kwargs['slug'] = parent_node.slug
        node_url = reverse('node_object', kwargs=url_kwargs)
        # Make sure user is authorized to see this node
        if node_id:
            if not (parent_node.access_level(request.user) in ['write', 'read']):
                new_url = reverse('django.contrib.auth.views.login')
                new_url += '?next=' + base_url + node_id + '/'
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
        if request.is_mobile:
            template = 'gtd/node_view_m.html'
        else:
            template = 'gtd/node_view.html'
        return render_to_response(template,
                                  locals(),
                                  RequestContext(request))

    def get_json(self, request, *args, **kwargs):
        """Returns the details of the node as a json encoded object"""
        node_id = kwargs.get('pk')
        node = get_object_or_404(Node, pk=node_id)
        return HttpResponse(
            serializers.serialize('json', [node])
        )

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
        base_url = reverse('node_object', kwargs=url_kwargs)
        breadcrumb_list = self.node.get_ancestors(include_self=True)
        # Make sure user is authorized to edit this node
        if self.node.access_level(request.user) != 'write':
            new_url = reverse('django.contrib.auth.views.login')
            new_url += '?next=' + base_url + node_id + '/'
            return redirect(new_url)
        if request.is_ajax():
            return self.ajax_post(request, *args, **kwargs)
        elif (request.method == "POST" and
              request.POST.get('function') == 'reorder'):
            # User is trying to move the node up or down
            if 'move_up' in request.POST:
                self.node.move_to(node.get_previous_sibling(),
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
            redirect_url = reverse('node_object', kwargs=url_kwargs)
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
            redirect_url = reverse('node_object', kwargs=url_kwargs)
            return redirect(redirect_url)
        elif request.method == "POST": # Form submission
            post = request.POST
            form = NodeForm(request.POST, instance=self.node)
            if form.is_valid():
                form.save()
                url_kwargs['pk'] = node_id
                redirect_url = reverse('node_object', kwargs=url_kwargs)
                return redirect(redirect_url)
        else: # Blank form
            form = NodeForm(instance=node)
        if request.is_mobile:
            template = 'gtd/node_edit_m.html'
        else:
            template = 'gtd/node_edit.html'
        return render_to_response(template,
                                  locals(),
                                  RequestContext(request))
    def ajax_post(self, request, *args, **kwargs):
        """Handles ajax interactions, eg. editing Node objects. Called from
        with self.post(). Mostly conducted through JSON format:
        {
          pk: [node primary key],
          model: (eg 'gtd.node'),
          fields: [dict of fields to change with new values]
        }

        Returns: JSON object of all node fields, with changes.
        """
        # Unpack arguments
        node_id = kwargs['pk']
        post = request.POST
        if post.get('form') == 'modal':
            # Form posted from the modal javascript dialog
            if post.get('todo_state') == '0':
                post.pop('todo_state')
            form = NodeForm(post, instance=self.node)
            if form.is_valid():
                if post.get('auto_update') == 'false':
                    form.auto_update = False
                form.save()
                self.node = Node.objects.get(pk=self.node.pk)
                # Prepare the response
                node_data = self.node.as_pre_json()
            else:
                print(form.errors)
                return HttpResponseBadRequest(form.errors)
        else: # if post.get('form') != 'modal':
            # Text
            self.node.set_fields(post)
            self.node.save()
            self.node = Node.objects.get(pk=self.node.pk)
        data = serializers.serialize('json', [self.node])
        return HttpResponse(json.dumps(data))


class TreeView(View):
    """Retrieves entire trees at once"""
    def get(self, request, *args, **kwargs):
        nodes = Node.objects.filter(tree_id=kwargs['tree_id'])
        return HttpResponse(serializers.serialize('json', nodes))


class Descendants(View):
    """Manages the retrieval of descendants of a given node"""
    def get(self, request, *args, **kwargs):
        ancestor_pk = self.kwargs['ancestor_pk']
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
            return HttpResponse(
                serializers.serialize('json', nodes_qs)
            )
        else:
            serializers.serialize('json', nodes_qs)
            # Non-ajax returns the base template to show django-debug-toolbar
            return render_to_response('base.html',
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
            if request.is_mobile:
                pages.append({
                    'url': '#',
                    'display': 'Page {0} of {1}'.format(page, num_pages)
                })
            else:
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
    base_url = reverse('node_object')
    if request.is_mobile:
        template = 'gtd/node_search_m.html'
    else:
        template = 'gtd/node_search.html'
    return render_to_response(template,
                              locals(),
                              RequestContext(request))
