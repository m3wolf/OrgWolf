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

from django.forms import ModelForm, TextInput
from GettingThingsDone.models import Node

class NodeForm(ModelForm):
    class Meta:
        fields = ('title', 'todo_state', 'project', 'scheduled', 'scheduled_time_specific', 'deadline', 'deadline_time_specific', 'priority', 'scope', 'repeats', 'repeating_number', 'repeating_unit', 'repeats_from_completion')
        model = Node
        widgets = {
            'title': TextInput(),
            }
